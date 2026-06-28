// Tags service endpoints. The gallery uses tags/query so each item also carries
// the current user's tag_status. Identity comes from the token (the gateway
// injects X-User-Id), so the frontend never sends a user id.
import { getToken } from "../auth/storage";
import { API_BASE_URL } from "../config";
import type { FileListResponse, LabelOption, TagStatus } from "../types";
import { ApiError, api } from "./client";
import type { FileQueryParams } from "./files";

export type SearchMode = "keyword" | "meaning";

export interface GalleryParams extends FileQueryParams {
  status?: TagStatus; // filter to only passed / failed
  labels?: string[]; // filter to files carrying any of these user labels
  // "meaning" routes the text query through CLIP semantic search instead of
  // caption keyword matching. Omitted/keyword keeps the default behaviour.
  search_mode?: SearchMode;
}

export interface SetTagsResult {
  tagged: number;
  skipped_missing: string[];
}

export interface RemoveTagsResult {
  removed: number;
}

export function queryGallery(params: GalleryParams): Promise<FileListResponse> {
  return api<FileListResponse>("/api/tags/query", { params });
}

export interface TagStatusResponse {
  file_id: string;
  status: TagStatus | null;
}

export function getTagStatus(fileId: string): Promise<TagStatusResponse> {
  return api<TagStatusResponse>("/api/tags/status", { params: { file_id: fileId } });
}

export function setTags(fileIds: string[], status: TagStatus): Promise<SetTagsResult> {
  return api<SetTagsResult>("/api/tags/set", {
    method: "POST",
    body: { file_ids: fileIds, status },
  });
}

export function removeTags(fileIds: string[]): Promise<RemoveTagsResult> {
  return api<RemoveTagsResult>("/api/tags/remove", {
    method: "POST",
    body: { file_ids: fileIds },
  });
}

// --- Labels (free-form, per-user) ------------------------------------------

export interface AddLabelResult {
  labeled: number;
  skipped_missing: string[];
  label: string;
}

export interface RemoveLabelResult {
  removed: number;
  label: string;
}

export function addLabel(fileIds: string[], label: string): Promise<AddLabelResult> {
  return api<AddLabelResult>("/api/tags/label_add", {
    method: "POST",
    body: { file_ids: fileIds, label },
  });
}

export function removeLabel(fileIds: string[], label: string): Promise<RemoveLabelResult> {
  return api<RemoveLabelResult>("/api/tags/label_remove", {
    method: "POST",
    body: { file_ids: fileIds, label },
  });
}

export function getLabels(fileId: string): Promise<{ file_id: string; labels: string[] }> {
  return api<{ file_id: string; labels: string[] }>("/api/tags/labels", {
    params: { file_id: fileId },
  });
}

export function getLabelOptions(): Promise<{ labels: LabelOption[] }> {
  return api<{ labels: LabelOption[] }>("/api/tags/label_options");
}

// Turns a download response into a saved file, honouring Content-Disposition.
async function triggerDownload(response: Response, fallbackName: string): Promise<void> {
  if (!response.ok) {
    throw new ApiError(response.status, "Export failed");
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match ? match[1] : fallbackName;

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
}

// Export the user's tagged subset (optionally only passed / failed).
export async function downloadExport(
  format: "json" | "csv",
  status?: TagStatus,
): Promise<void> {
  const url = new URL("/api/tags/export", API_BASE_URL);
  url.searchParams.set("format", format);
  if (status) url.searchParams.set("status", status);

  const response = await fetch(url.toString(), { headers: authHeaders() });
  await triggerDownload(response, `tags.${format}`);
}

// Filters that drive a filter-based export. Mirrors the gallery query (text
// search + facet filters + tag status), minus pagination/sort. An empty object
// means "everything".
export type FilteredExportParams = Omit<
  GalleryParams,
  "page" | "page_size" | "sort" | "ids"
>;

// "report" = rich annotation file (status + labels, re-importable).
// "training" = ML-ready manifest (image + captions, triage stripped).
export type ExportPurpose = "report" | "training";
export type ExportFormat = "json" | "jsonl" | "csv";

// Export every file matching the given filters (text search, facets, tag
// status). Passing an empty object exports the whole dataset.
export async function downloadExportFiltered(
  filters: FilteredExportParams,
  format: ExportFormat,
  purpose: ExportPurpose = "report",
): Promise<void> {
  const url = new URL("/api/tags/export_filtered", API_BASE_URL);
  url.searchParams.set("format", format);
  url.searchParams.set("purpose", purpose);
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) url.searchParams.append(key, String(item));
    } else {
      url.searchParams.set(key, String(value));
    }
  }
  const response = await fetch(url.toString(), { headers: authHeaders() });
  await triggerDownload(response, `filtered.${format}`);
}

// Export an explicit set of files (the current selection), regardless of tag.
export async function downloadExportSelected(
  fileIds: string[],
  format: ExportFormat,
  purpose: ExportPurpose = "report",
): Promise<void> {
  const url = new URL("/api/tags/export_selected", API_BASE_URL);
  url.searchParams.set("format", format);
  url.searchParams.set("purpose", purpose);

  const response = await fetch(url.toString(), {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ file_ids: fileIds }),
  });
  await triggerDownload(response, `selected.${format}`);
}
