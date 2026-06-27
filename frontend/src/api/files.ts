// Files service endpoints (dataset metadata + filter options).
import type { FileItem, FileListResponse, OptionsResponse } from "../types";
import { api } from "./client";
import type { QueryValue } from "./client";

export type CaptionLength = "short" | "medium" | "long";
export type Orientation = "portrait" | "landscape" | "square";
export type Agreement = "high" | "low";
export type SortKey = "id" | "length" | "agreement" | "random";

// Shared filter/pagination params accepted by files/list and tags/query.
export interface FileQueryParams {
  page?: number;
  page_size?: number;
  q?: string;
  dataset?: string;
  split?: string;
  length?: CaptionLength;
  orientation?: Orientation;
  agreement?: Agreement;
  min_agreement?: number;
  sort?: SortKey;
  ids?: string[];
  // index signature so these are assignable to the client's params type
  [key: string]: QueryValue;
}

export function getOptions(): Promise<OptionsResponse> {
  return api<OptionsResponse>("/api/files/options");
}

export function getFile(id: string): Promise<FileItem> {
  return api<FileItem>("/api/files/get", { params: { id } });
}

export function listFiles(params: FileQueryParams): Promise<FileListResponse> {
  return api<FileListResponse>("/api/files/list", { params });
}
