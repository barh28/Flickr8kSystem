// Statistics endpoints: dataset-wide stats from the files service and the
// current user's tagging/labeling summary from the tags service.
import type { FilesStats, TagsStats } from "../types";
import { api } from "./client";

export function getFilesStats(): Promise<FilesStats> {
  return api<FilesStats>("/api/files/stats");
}

export function getTagsStats(): Promise<TagsStats> {
  return api<TagsStats>("/api/tags/stats");
}
