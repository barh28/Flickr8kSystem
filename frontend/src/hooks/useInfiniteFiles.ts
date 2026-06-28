import { useInfiniteQuery } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { queryGallery } from "../api/tags";
import type { GalleryParams } from "../api/tags";

function isIndexBuilding(error: unknown): boolean {
  return error instanceof ApiError && error.status === 503;
}

// Infinite gallery: fetches page-by-page and accumulates results. The query key
// excludes `page`, so changing any filter starts a fresh stream from page 1.
export function useInfiniteFiles(
  params: Omit<GalleryParams, "page">,
  options?: { enabled?: boolean },
) {
  return useInfiniteQuery({
    queryKey: ["gallery", params],
    queryFn: ({ pageParam }) => queryGallery({ ...params, page: pageParam }),
    initialPageParam: 1,
    enabled: options?.enabled ?? true,
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.page * lastPage.page_size;
      return loaded < lastPage.total ? lastPage.page + 1 : undefined;
    },
    // Gallery errors are surfaced inline (including the CLIP "index building"
    // state), so we don't also raise a global toast for them.
    meta: { suppressErrorToast: true },
    retry: (failureCount, error) => !isIndexBuilding(error) && failureCount < 1,
    refetchInterval: (query) => (isIndexBuilding(query.state.error) ? 5000 : false),
  });
}
