// Shared API types, mirroring the backend service responses.

export type TagStatus = "passed" | "failed";

export interface AuthUser {
  user_id: string;
  username: string;
}

export interface AuthResponse {
  user_id: string;
  username: string;
  token: string;
}

export interface FileItem {
  id: string;
  image_url: string;
  dataset: string;
  split: string;
  width: number;
  height: number;
  orientation: "portrait" | "landscape" | "square";
  captions: string[];
  caption_length: number;
  agreement: number;
  // present on tags/query results, absent on plain files/list
  tag_status?: TagStatus | null;
  labels?: string[];
}

export interface LabelOption {
  label: string;
  count: number;
}

export interface FileListResponse {
  total: number;
  page: number;
  page_size: number;
  items: FileItem[];
}

export interface OptionsResponse {
  datasets: string[];
  splits: string[];
  orientations: string[];
  word_count: { min: number; max: number };
}

export interface Bucket {
  label: string;
  count: number;
}

export interface FilesStats {
  total: number;
  by_split: Bucket[];
  by_orientation: Bucket[];
  caption_length: { min: number; max: number; avg: number; buckets: Bucket[] };
  agreement: { avg: number; buckets: Bucket[] };
}

export interface TagsStats {
  passed: number;
  failed: number;
  tagged_total: number;
  labels: LabelOption[];
}
