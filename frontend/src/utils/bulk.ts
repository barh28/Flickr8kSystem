// Parse an uploaded file of image IDs (optionally with status/labels) for bulk
// tagging. Supports JSON (array of ids or array of objects), CSV (with or
// without a header), and plain TXT (one id per line). Parsing is done in the
// browser; the result is applied via the existing tags endpoints.

export type BulkStatus = "passed" | "failed";

export interface BulkRow {
  id: string;
  status?: BulkStatus;
  labels?: string[];
}

export interface BulkParseResult {
  rows: BulkRow[];
  hasStatus: boolean;
  hasLabel: boolean;
}

const ID_KEYS = ["id", "image_id", "file_id", "image", "filename"];
// Accept both the singular `label` and the plural `labels` (the latter is what
// the export writes), so an exported file round-trips back through bulk import.
const LABEL_KEYS = ["labels", "label"];

function normStatus(value: unknown): BulkStatus | undefined {
  const s = String(value ?? "").trim().toLowerCase();
  if (s === "passed" || s === "pass") return "passed";
  if (s === "failed" || s === "fail") return "failed";
  return undefined;
}

// A label cell may hold several labels joined by "|" (the export's CSV format)
// or be a JSON array. Normalize everything to a trimmed, de-duped string list.
function toLabels(value: unknown): string[] {
  if (value == null) return [];
  const raw = Array.isArray(value)
    ? value.map((item) => String(item))
    : String(value).split("|");
  const seen = new Set<string>();
  for (const item of raw) {
    const trimmed = item.trim();
    if (trimmed) seen.add(trimmed);
  }
  return [...seen];
}

function getField(obj: Record<string, unknown>, keys: string[]): unknown {
  for (const key of keys) {
    if (obj[key] !== undefined && obj[key] !== null) return obj[key];
  }
  return undefined;
}

// Minimal CSV cell split: trims and strips a single pair of surrounding quotes.
function splitCsv(line: string): string[] {
  return line.split(",").map((cell) => cell.trim().replace(/^"(.*)"$/, "$1"));
}

function parseJson(text: string): BulkRow[] {
  const data: unknown = JSON.parse(text);
  const list: unknown[] = Array.isArray(data)
    ? data
    : data && typeof data === "object" && Array.isArray((data as Record<string, unknown>).items)
      ? ((data as Record<string, unknown>).items as unknown[])
      : [];

  const rows: BulkRow[] = [];
  for (const entry of list) {
    if (typeof entry === "string") {
      const id = entry.trim();
      if (id) rows.push({ id });
      continue;
    }
    if (entry && typeof entry === "object") {
      const obj = entry as Record<string, unknown>;
      const id = String(getField(obj, ID_KEYS) ?? "").trim();
      if (!id) continue;
      const status = normStatus(obj.status);
      const labels = toLabels(getField(obj, LABEL_KEYS));
      rows.push({ id, status, labels: labels.length > 0 ? labels : undefined });
    }
  }
  return rows;
}

function parseDelimited(text: string): BulkRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length === 0) return [];

  const header = splitCsv(lines[0]).map((cell) => cell.toLowerCase());
  const hasHeader = header.some((cell) => ID_KEYS.includes(cell));

  // With a header we honor the named columns. Without one we fall back to a
  // fixed positional order: id, status, label (extra columns are ignored, and a
  // single-column line of just IDs still works since status/label stay empty).
  let idIdx = 0;
  let statusIdx = 1;
  let labelIdx = 2;
  let start = 0;
  if (hasHeader) {
    idIdx = header.findIndex((cell) => ID_KEYS.includes(cell));
    statusIdx = header.indexOf("status");
    labelIdx = header.findIndex((cell) => LABEL_KEYS.includes(cell));
    start = 1;
  }

  const rows: BulkRow[] = [];
  for (let i = start; i < lines.length; i++) {
    const cells = splitCsv(lines[i]);
    const id = (cells[idIdx] ?? "").trim();
    if (!id) continue;
    const status = statusIdx >= 0 ? normStatus(cells[statusIdx]) : undefined;
    const labels = labelIdx >= 0 ? toLabels(cells[labelIdx]) : [];
    rows.push({ id, status, labels: labels.length > 0 ? labels : undefined });
  }
  return rows;
}

export function parseBulkFile(text: string, filename: string): BulkParseResult {
  const trimmed = text.trim();
  const looksJson =
    filename.toLowerCase().endsWith(".json") ||
    trimmed.startsWith("[") ||
    trimmed.startsWith("{");

  let rows = looksJson ? parseJson(trimmed) : parseDelimited(trimmed);

  // De-duplicate ids, keeping the first occurrence.
  const seen = new Set<string>();
  rows = rows.filter((row) => {
    if (seen.has(row.id)) return false;
    seen.add(row.id);
    return true;
  });

  return {
    rows,
    hasStatus: rows.some((row) => row.status),
    hasLabel: rows.some((row) => (row.labels?.length ?? 0) > 0),
  };
}
