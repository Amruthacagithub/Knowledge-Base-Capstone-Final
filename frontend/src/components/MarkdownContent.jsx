import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useMemo,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const CitationContext = createContext({
  onCitationClick: null,
  selectedMarker: null,
});

/**
 * Split text into parts, turning [1], [2] citation markers into clickable pills.
 */
function renderWithCitations(text, onCitationClick, selectedMarker) {
  if (!text || !onCitationClick) return text;
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const num = Number.parseInt(match[1], 10);
      return (
        <button
          key={`cite-${i}-${num}`}
          type="button"
          className={`citation-pill ${selectedMarker === num ? "active" : ""}`}
          onClick={(e) => {
            e.preventDefault();
            onCitationClick(num);
          }}
        >
          {num}
        </button>
      );
    }
    return part;
  });
}

function TextWithCitations({ children, onCitationClick, selectedMarker }) {
  if (typeof children !== "string") {
    if (Array.isArray(children)) {
      return children.map((child) =>
        typeof child === "string"
          ? renderWithCitations(child, onCitationClick, selectedMarker)
          : child
      );
    }
    return children;
  }
  return <>{renderWithCitations(children, onCitationClick, selectedMarker)}</>;
}

const wrapText = (tagName) =>
  function WrappedText({ children, ...props }) {
    const citationContext = useContext(CitationContext);
    return createElement(
      tagName,
      props,
      <TextWithCitations {...citationContext}>{children}</TextWithCitations>
    );
  };

function Strong({ children }) {
  return <strong>{children}</strong>;
}

function Emphasis({ children }) {
  return <em>{children}</em>;
}

function Heading1({ children }) {
  return <h1 className="md-h1">{children}</h1>;
}

function Heading2({ children }) {
  return <h2 className="md-h2">{children}</h2>;
}

function Heading3({ children }) {
  return <h3 className="md-h3">{children}</h3>;
}

function UnorderedList({ children }) {
  return <ul className="md-ul">{children}</ul>;
}

function OrderedList({ children }) {
  return <ol className="md-ol">{children}</ol>;
}

function Table({ children }) {
  return (
    <div className="md-table-wrap">
      <table className="md-table">{children}</table>
    </div>
  );
}

function Code({ className, children, ...props }) {
  if (!className) {
    return (
      <code className="md-code-inline" {...props}>
        {children}
      </code>
    );
  }
  return (
    <pre className="md-pre">
      <code className={className} {...props}>
        {children}
      </code>
    </pre>
  );
}

const MARKDOWN_COMPONENTS = {
  p: wrapText("p"),
  li: wrapText("li"),
  td: wrapText("td"),
  th: wrapText("th"),
  strong: Strong,
  em: Emphasis,
  h1: Heading1,
  h2: Heading2,
  h3: Heading3,
  ul: UnorderedList,
  ol: OrderedList,
  table: Table,
  code: Code,
};

export default function MarkdownContent({
  content,
  className = "markdown-body",
  variant = "answer",
  citations = [],
  onCitationClick,
  selectedMarker = null,
}) {
  const handleCitationClick = useCallback(
    (marker) => {
      if (!onCitationClick || !citations?.length) return;
      const citation = citations.find((item) => item.marker === marker);
      if (citation) onCitationClick(citation);
    },
    [citations, onCitationClick]
  );
  const citationContext = useMemo(
    () => ({ onCitationClick: handleCitationClick, selectedMarker }),
    [handleCitationClick, selectedMarker]
  );

  if (!content?.trim()) {
    return <p className={className}>No content available.</p>;
  }

  return (
    <div className={`${className} markdown-${variant}`}>
      <CitationContext.Provider
        value={citationContext}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
          {content}
        </ReactMarkdown>
      </CitationContext.Provider>
    </div>
  );
}
