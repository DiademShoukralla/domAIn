from dataclasses import dataclass

import tiktoken

from domain.config import get_settings


@dataclass(frozen=True)
class DocumentChunk:
    document_id: str
    chunk_index: int
    content: str
    heading_hierarchy: list[str]


def _get_encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str, encoder: tiktoken.Encoding) -> int:
    return len(encoder.encode(text))


def _split_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading: list[str] = []
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append(("\n".join(current_lines).strip(), current_heading.copy()))
                current_lines = []
            level = len(line) - len(line.lstrip("#"))
            heading = line.lstrip("#").strip()
            current_heading = current_heading[: max(level - 1, 0)] + [heading]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append(("\n".join(current_lines).strip(), current_heading.copy()))

    if not sections and text.strip():
        sections.append((text.strip(), []))

    return sections


def chunk_text(document_id: str, text: str) -> list[DocumentChunk]:
    settings = get_settings()
    encoder = _get_encoder()
    target = settings.chunk_target_tokens
    overlap = settings.chunk_overlap_tokens

    sections = _split_sections(text)
    if not sections:
        return []

    chunks: list[DocumentChunk] = []
    chunk_index = 0
    buffer = ""
    buffer_heading: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer, buffer_heading, chunk_index
        content = buffer.strip()
        if not content:
            return
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                heading_hierarchy=buffer_heading.copy(),
            )
        )
        chunk_index += 1
        if overlap > 0:
            tokens = encoder.encode(content)
            overlap_tokens = tokens[-overlap:] if len(tokens) > overlap else tokens
            buffer = encoder.decode(overlap_tokens)
        else:
            buffer = ""
            buffer_heading = []

    for section_text, heading in sections:
        paragraphs = [part.strip() for part in section_text.split("\n\n") if part.strip()]
        if not paragraphs:
            paragraphs = [section_text] if section_text else []

        for paragraph in paragraphs:
            candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
            if _count_tokens(candidate, encoder) <= target:
                buffer = candidate
                buffer_heading = heading
            else:
                flush_buffer()
                buffer = paragraph
                buffer_heading = heading
                while _count_tokens(buffer, encoder) > target:
                    tokens = encoder.encode(buffer)
                    piece = encoder.decode(tokens[:target])
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            chunk_index=chunk_index,
                            content=piece,
                            heading_hierarchy=buffer_heading.copy(),
                        )
                    )
                    chunk_index += 1
                    buffer = encoder.decode(tokens[target - overlap : target]) if overlap else ""

    flush_buffer()
    return chunks
