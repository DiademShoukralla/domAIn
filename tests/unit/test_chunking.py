from domain.ingestion.chunking import chunk_text


def test_chunk_text_splits_markdown_sections() -> None:
    text = "# Title\n\nFirst paragraph.\n\n## Section\n\nSecond paragraph with details."
    chunks = chunk_text("docs/readme.md", text)
    assert len(chunks) >= 1
    assert chunks[0].document_id == "docs/readme.md"
    assert "First paragraph" in chunks[0].content or "Second paragraph" in chunks[-1].content
