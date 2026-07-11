/**
 * Find excerpt position in document content (fuzzy match).
 */
import { excerptForHighlight } from "./citationExcerpt";

function normalizeWhitespace(s) {
  return s.replace(/\s+/g, " ").trim();
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`);
}

/**
 * Build candidate needles (longest first) for matching a chunk in full document text.
 */
export function buildHighlightNeedles(excerpt) {
  if (!excerpt?.trim()) return [];

  const text = excerpt.trim();
  const needles = new Set();

  const add = (value) => {
    if (value?.trim()) needles.add(value.trim());
  };

  add(text);
  add(excerptForHighlight(text, 800));
  add(excerptForHighlight(text, 480));

  const strippedMd = text.replace(/^#{1,6}\s+/gm, "").trim();
  if (strippedMd !== text) {
    add(strippedMd);
    add(excerptForHighlight(strippedMd, 480));
  }

  for (const len of [400, 300, 200, 120, 80, 50]) {
    if (text.length >= len) {
      add(text.slice(0, len));
      add(text.slice(-len));
    }
  }

  return [...needles].sort((a, b) => b.length - a.length);
}

/**
 * Word-sequence match tolerates whitespace / line-break differences.
 */
function findByWordSequence(content, excerpt) {
  const words = normalizeWhitespace(excerpt).split(" ").filter((w) => w.length > 1);
  if (words.length < 4) return null;

  const pattern = words.map(escapeRegex).join(String.raw`\s+`);
  try {
    const re = new RegExp(pattern, "i");
    const m = re.exec(content);
    if (m) {
      return { start: m.index, end: m.index + m[0].length, needle: m[0] };
    }
  } catch {
    return null;
  }
  return null;
}

function exactRange(content, needle) {
  const start = content.indexOf(needle);
  if (start === -1) return null;
  return { start, end: start + needle.length, needle };
}

function normalizedRange(content, needle) {
  const normalizedNeedle = normalizeWhitespace(needle);
  if (normalizedNeedle.length < 40) return null;
  if (!normalizeWhitespace(content).includes(normalizedNeedle)) return null;
  return findByWordSequence(content, normalizedNeedle);
}

function shortenedRange(content, needle) {
  for (const length of [300, 200, 120, 80, 50]) {
    if (needle.length < length) continue;
    const shortened = needle.slice(0, length);
    const range =
      exactRange(content, shortened) || findByWordSequence(content, shortened);
    if (range) return range;
  }
  return null;
}

function findExcerptRangeOnce(content, excerpt) {
  if (!content || !excerpt?.trim()) return null;

  const needle = excerpt.trim();
  return (
    exactRange(content, needle) ||
    normalizedRange(content, needle) ||
    shortenedRange(content, needle) ||
    findByWordSequence(content, needle)
  );
}

export function findExcerptRange(content, excerpt) {
  if (!content || !excerpt?.trim()) return null;

  for (const needle of buildHighlightNeedles(excerpt)) {
    const range = findExcerptRangeOnce(content, needle);
    if (range) return range;
  }
  return null;
}

/**
 * Split document text into before / match / after for a single excerpt.
 */
export function splitByExcerpt(content, excerpt) {
  const range = findExcerptRange(content, excerpt);
  if (!range) {
    return { before: content || "", match: null, after: "" };
  }
  return {
    before: content.slice(0, range.start),
    match: content.slice(range.start, range.end),
    after: content.slice(range.end),
  };
}

/**
 * Split content into alternating normal / highlight segments for multiple excerpts.
 */
export function splitByExcerpts(content, excerpts) {
  if (!content) return [{ type: "normal", text: "" }];

  const uniqueNeedles = normalizeExcerpts(excerpts);
  if (!uniqueNeedles.length) {
    return [{ type: "normal", text: content }];
  }

  const ranges = findExcerptRanges(content, uniqueNeedles);
  if (!ranges.length) {
    return [{ type: "normal", text: content }];
  }

  return rangesToSegments(content, mergeRanges(ranges));
}

function normalizeExcerpts(excerpts) {
  const raw = Array.isArray(excerpts) ? excerpts : [excerpts];
  const needles = raw
    .flatMap((e) => {
      if (typeof e !== "string" || !e.trim()) return [];
      const trimmed = e.trim();
      if (trimmed.length <= 700) return [trimmed];
      return buildHighlightNeedles(trimmed);
    })
    .filter(Boolean);
  return [...new Set(needles)];
}

function findExcerptRanges(content, uniqueNeedles) {
  const ranges = [];
  for (const excerpt of uniqueNeedles) {
    const range = findExcerptRangeOnce(content, excerpt);
    if (range) ranges.push(range);
  }
  return ranges;
}

function mergeRanges(ranges) {
  ranges.sort((a, b) => a.start - b.start);
  const merged = [];
  for (const range of ranges) {
    const last = merged.at(-1);
    if (!last || range.start > last.end) {
      merged.push({ ...range });
    } else {
      last.end = Math.max(last.end, range.end);
    }
  }
  return merged;
}

function rangesToSegments(content, ranges) {
  const segments = [];
  let position = 0;
  for (const range of ranges) {
    if (range.start > position) {
      segments.push({
        type: "normal",
        text: content.slice(position, range.start),
      });
    }
    segments.push({
      type: "highlight",
      text: content.slice(range.start, range.end),
    });
    position = range.end;
  }
  if (position < content.length) {
    segments.push({ type: "normal", text: content.slice(position) });
  }
  return segments;
}
