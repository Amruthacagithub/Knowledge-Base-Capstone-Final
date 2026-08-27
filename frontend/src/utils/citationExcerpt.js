/**
 * Build a focused excerpt for highlight matching (not the full chunk).
 */
export function excerptForHighlight(chunkText, maxLen = 480) {
  if (!chunkText?.trim()) return null;
  const text = chunkText.trim();
  if (text.length <= maxLen) return text;

  const cut = text.slice(0, maxLen);
  const sentenceEnd = Math.max(
    cut.lastIndexOf(". "),
    cut.lastIndexOf(".\n"),
    cut.lastIndexOf("! "),
    cut.lastIndexOf("? ")
  );
  if (sentenceEnd > 60) {
    return cut.slice(0, sentenceEnd + 1).trim();
  }
  const wordCut = cut.lastIndexOf(" ");
  if (wordCut > 40) return cut.slice(0, wordCut).trim();
  return cut.trim();
}

function excerptFromOffset(text, start, maxLen) {
  const slice = text.slice(start, start + maxLen);
  if (slice.length <= maxLen) return slice.trim();
  const sentenceEnd = Math.max(
    slice.lastIndexOf(". "),
    slice.lastIndexOf(".\n"),
    slice.lastIndexOf("! "),
    slice.lastIndexOf("? ")
  );
  if (sentenceEnd > 40) return slice.slice(0, sentenceEnd + 1).trim();
  const wordCut = slice.lastIndexOf(" ");
  if (wordCut > 30) return slice.slice(0, wordCut).trim();
  return slice.trim();
}

/**
 * Needles for highlighting the most relevant parts of a chunk (head, tail, paragraphs).
 */
export function buildFocusNeedles(chunkText) {
  if (!chunkText?.trim()) return [];

  const text = chunkText.trim();
  const needles = new Set();

  const add = (value) => {
    if (value?.trim()) needles.add(value.trim());
  };

  add(excerptForHighlight(text, 400));
  if (text.length > 350) {
    add(excerptFromOffset(text, Math.max(0, text.length - 500), 450));
  }

  for (const block of text.split(/\n\n+/)) {
    const blockText = block.trim();
    if (blockText.length >= 24 && blockText.length <= 700) {
      add(blockText);
    }
    for (const line of blockText.split("\n")) {
      const lineText = line.replace(/^[-*]\s+/, "").trim();
      if (lineText.length >= 24 && lineText.length <= 400) {
        add(lineText);
      }
    }
  }

  return [...needles].sort((a, b) => b.length - a.length);
}

/**
 * Shorter text for source-card previews — tries to include a highlightable passage.
 */
export function previewExcerpt(chunkText, maxLen = 420) {
  if (!chunkText?.trim()) return "";
  const text = chunkText.trim();
  if (text.length <= maxLen) return text;

  const needles = buildFocusNeedles(text);
  const ranked = [...needles].sort((a, b) => _previewNeedleScore(b) - _previewNeedleScore(a));
  for (const needle of ranked) {
    const anchor = needle.length > 80 ? needle.slice(0, 80) : needle;
    const idx = text.indexOf(anchor);
    if (idx >= 0) {
      const start = Math.max(0, idx - 30);
      const slice = text.slice(start, start + maxLen);
      const prefix = start > 0 ? "…" : "";
      const suffix = start + maxLen < text.length ? "…" : "";
      return `${prefix}${slice.trim()}${suffix}`;
    }
  }

  return fallbackPreview(text, maxLen);
}

function fallbackPreview(text, maxLen) {
  const cut = text.slice(0, maxLen);
  const paraEnd = cut.lastIndexOf("\n\n");
  if (paraEnd > 120) return `${cut.slice(0, paraEnd).trim()}…`;

  const sentenceEnd = Math.max(
    cut.lastIndexOf(". "),
    cut.lastIndexOf(".\n"),
    cut.lastIndexOf("! "),
    cut.lastIndexOf("? ")
  );
  if (sentenceEnd > 80) return `${cut.slice(0, sentenceEnd + 1).trim()}…`;

  const wordCut = cut.lastIndexOf(" ");
  if (wordCut > 60) return `${cut.slice(0, wordCut).trim()}…`;
  return `${cut.trim()}…`;
}

function _previewNeedleScore(needle) {
  let score = 0;
  if (/cash|carryover|accrue|expire|pto cannot/i.test(needle)) score += 12;
  if (needle.length > 35 && needle.length < 400) score += 4;
  if (/^#{1,6}\s/.test(needle)) score -= 6;
  return score;
}
