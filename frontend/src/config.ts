// The frontend talks ONLY to the API gateway. Override via VITE_API_BASE_URL.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

// Default page size for the gallery (server-side paginated).
export const DEFAULT_PAGE_SIZE = 50;

// Build a full image URL from a file's relative image_url (e.g. "/images/x.jpg").
// The gateway serves these statically.
export function imageSrc(imageUrl: string): string {
  return `${API_BASE_URL}${imageUrl}`;
}
