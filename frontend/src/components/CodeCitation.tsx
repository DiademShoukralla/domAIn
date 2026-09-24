import type { Citation } from "../types/chat";

interface CodeCitationProps {
  citation: Citation;
}

function splitExcerptLines(excerpt: string): string[] {
  return excerpt.replace(/\r\n/g, "\n").split("\n");
}

export function CodeCitation({ citation }: CodeCitationProps) {
  const lines = splitExcerptLines(citation.excerpt);
  const startLine = citation.chunk_index + 1;

  return (
    <figure className="dom-code-citation">
      <figcaption className="dom-code-citation__source code-sm">
        {citation.document_id} · lines {startLine}–{startLine + Math.max(lines.length - 1, 0)}
      </figcaption>
      <div className="dom-code-citation__scroll">
        <ol className="dom-code-citation__lines">
          {lines.map((line, index) => (
            <li
              key={`${citation.document_id}-${index}`}
              className={`dom-code-citation__line${index === 0 ? " dom-code-citation__line--hit" : ""}`}
              data-line={startLine + index}
            >
              <span className="dom-tok-pun">{line || " "}</span>
            </li>
          ))}
        </ol>
      </div>
    </figure>
  );
}
