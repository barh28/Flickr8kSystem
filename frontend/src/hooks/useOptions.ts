import { useQuery } from "@tanstack/react-query";

import { getOptions } from "../api/files";

// Filter options change rarely (dataset is loaded once), so cache aggressively.
export function useOptions() {
  return useQuery({
    queryKey: ["options"],
    queryFn: getOptions,
    staleTime: Infinity,
  });
}
