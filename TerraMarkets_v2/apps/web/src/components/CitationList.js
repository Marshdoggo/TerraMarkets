import Link from "next/link";

export default function CitationList({ citations = [], title = "Citations" }) {
  if (!citations.length) {
    return null;
  }

  return (
    <div className="stack">
      <strong>{title}</strong>
      {citations.map((citation, index) => (
        <div className="muted" key={`${citation.type || "citation"}:${citation.url || citation.display_text || index}`}>
          {citation.url ? (
            <Link href={citation.url} target="_blank" rel="noreferrer">
              {citation.title || citation.display_text || citation.url}
            </Link>
          ) : (
            <span>{citation.display_text || citation.label || "Reference"}</span>
          )}
          {citation.domain ? <span>{` · ${citation.domain}`}</span> : null}
          {citation.type ? <span>{` · ${citation.type.replace("_", " ")}`}</span> : null}
        </div>
      ))}
    </div>
  );
}
