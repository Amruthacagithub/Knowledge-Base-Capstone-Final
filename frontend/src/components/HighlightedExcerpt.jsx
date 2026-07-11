import MarkdownContent from "./MarkdownContent";
import { splitByExcerpts } from "../utils/highlightContent";
import { buildFocusNeedles } from "../utils/citationExcerpt";

/**
 * Renders chunk text with yellow highlights on cited passages (not the whole chunk).
 */
export default function HighlightedExcerpt({
  content,
  highlightSource,
  variant = "source",
  className = "",
}) {
  if (!content?.trim()) return null;

  const focusNeedles = buildFocusNeedles(highlightSource || content);
  const segments = splitByExcerpts(content, focusNeedles);
  const hasHighlight = segments.some((s) => s.type === "highlight");

  if (!hasHighlight) {
    return (
      <MarkdownContent
        content={content}
        variant={variant}
        className={`markdown-body markdown-source ${className}`.trim()}
      />
    );
  }

  return (
    <div className={`highlighted-excerpt ${className}`.trim()}>
      {segments.map((seg, i) => {
        if (!seg.text?.trim()) return null;
        if (seg.type === "highlight") {
          return (
            <div key={i} className="excerpt-highlight-block">
              <MarkdownContent
                content={seg.text}
                variant={variant}
                className="markdown-body markdown-source"
              />
            </div>
          );
        }
        return (
          <MarkdownContent
            key={i}
            content={seg.text}
            variant={variant}
            className="markdown-body markdown-source"
          />
        );
      })}
    </div>
  );
}
