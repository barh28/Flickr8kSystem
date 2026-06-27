import { useInfiniteQuery } from "@tanstack/react-query";

import { queryGallery } from "../api/tags";
import type { GalleryParams } from "../api/tags";

// Infinite gallery: fetches page-by-page and accumulates results. The query key
// excludes `page`, so changing any filter starts a fresh stream from page 1.
export function useInfiniteFiles(params: Omit<GalleryParams, "page">) {
  return useInfiniteQuery({
    queryKey: ["gallery", params],
    queryFn: ({ pageParam }) => queryGallery({ ...params, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.page * lastPage.page_size;
      return loaded < lastPage.total ? lastPage.page + 1 : undefined;
    },
  });
}
