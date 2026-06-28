import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import type { CaptionLength, Orientation, SortKey } from "../api/files";
import {
  addLabel,
  downloadExportFiltered,
  downloadExportSelected,
  getLabelOptions,
  removeLabel,
  removeTags,
  setTags,
} from "../api/tags";
import type { GalleryParams, SearchMode } from "../api/tags";
import Button from "../components/common/Button";
import Spinner from "../components/common/Spinner";
import BulkTagModal from "../components/explorer/BulkTagModal";
import FiltersPanel from "../components/explorer/FiltersPanel";
import type { GalleryFilters } from "../components/explorer/FiltersPanel";
import GalleryToolbar from "../components/explorer/GalleryToolbar";
import type {
  ExportFormat,
  ExportPurpose,
  ExportScope,
} from "../components/explorer/GalleryToolbar";
import ImageGrid from "../components/explorer/ImageGrid";
import SearchBar from "../components/explorer/SearchBar";
import { DEFAULT_PAGE_SIZE } from "../config";
import { useInfiniteFiles } from "../hooks/useInfiniteFiles";
import { useOptions } from "../hooks/useOptions";
import { toast } from "../toast/toastStore";
import type { TagStatus } from "../types";
import styles from "./css/ExplorerPage.module.css";

const FILTER_KEYS: (keyof GalleryFilters)[] = [
  "q",
  "dataset",
  "split",
  "length",
  "orientation",
  "min_agreement",
  "status",
  "sort",
];

export default function ExplorerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: options } = useOptions();

  const filters: GalleryFilters = {
    q: searchParams.get("q") ?? "",
    dataset: searchParams.get("dataset") ?? "",
    split: searchParams.get("split") ?? "",
    length: searchParams.get("length") ?? "",
    orientation: searchParams.get("orientation") ?? "",
    min_agreement: searchParams.get("min_agreement") ?? "",
    status: searchParams.get("status") ?? "",
    sort: searchParams.get("sort") ?? "id",
    search_mode: searchParams.get("search_mode") ?? "keyword",
  };

  const searchMode: SearchMode = filters.search_mode === "meaning" ? "meaning" : "keyword";

  // Labels are multi-valued, so they live as repeated ?labels= params.
  const selectedLabels = searchParams.getAll("labels");

  const hasActiveFilters =
    searchMode === "meaning" ||
    selectedLabels.length > 0 ||
    FILTER_KEYS.some((key) => key !== "sort" && filters[key] !== "");

  function setFilter(key: keyof GalleryFilters, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    });
  }

  function toggleLabel(label: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      const current = next.getAll("labels");
      next.delete("labels");
      const updated = current.includes(label)
        ? current.filter((item) => item !== label)
        : [...current, label];
      for (const item of updated) next.append("labels", item);
      return next;
    });
  }

  function clearFilters() {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      for (const key of FILTER_KEYS) next.delete(key);
      next.delete("labels");
      next.delete("search_mode");
      return next;
    });
  }

  const meaningWithoutQuery = searchMode === "meaning" && !filters.q.trim();

  const params: Omit<GalleryParams, "page"> = {
    page_size: DEFAULT_PAGE_SIZE,
    q: filters.q.trim() || undefined,
    dataset: filters.dataset || undefined,
    split: filters.split || undefined,
    length: (filters.length || undefined) as CaptionLength | undefined,
    orientation: (filters.orientation || undefined) as Orientation | undefined,
    min_agreement: filters.min_agreement ? Number(filters.min_agreement) : undefined,
    status: (filters.status || undefined) as TagStatus | undefined,
    labels: selectedLabels.length > 0 ? selectedLabels : undefined,
    sort: filters.sort as SortKey,
    search_mode: searchMode === "meaning" ? "meaning" : undefined,
  };

  const { data: labelOptions } = useQuery({
    queryKey: ["label-options"],
    queryFn: getLabelOptions,
  });

  const {
    data,
    isLoading,
    isError,
    error,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useInfiniteFiles(params, { enabled: !meaningWithoutQuery });

  // The CLIP service answers 503 while it is still building its image index on
  // first boot; show a friendlier, retryable message in that case.
  const indexBuilding =
    isError && error instanceof ApiError && error.status === 503;

  const items = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  // Multi-select + tagging.
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showBulk, setShowBulk] = useState(false);

  // Selection belongs to a specific result set. When the filters/search/sort
  // change (the URL changes), the visible images change, so start fresh.
  // Note: infinite-scroll page loads don't touch the URL, so they're unaffected.
  const filterKey = searchParams.toString();
  useEffect(() => {
    setSelected(new Set());
  }, [filterKey]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function clearSelection() {
    setSelected(new Set());
  }

  function selectAll() {
    setSelected(new Set(items.map((item) => item.id)));
  }

  function refreshAndClear() {
    queryClient.invalidateQueries({ queryKey: ["gallery"] });
    clearSelection();
  }

  const tagMutation = useMutation({
    mutationFn: (status: TagStatus) => setTags([...selected], status),
    onSuccess: (result, status) => {
      toast.success(`Tagged ${result.tagged} image(s) as ${status}.`);
      refreshAndClear();
    },
  });

  const untagMutation = useMutation({
    mutationFn: () => removeTags([...selected]),
    onSuccess: (result) => {
      toast.success(`Removed tags from ${result.removed} image(s).`);
      refreshAndClear();
    },
  });

  const labelMutation = useMutation({
    mutationFn: (label: string) => addLabel([...selected], label),
    onSuccess: (result) => {
      toast.success(`Labeled ${result.labeled} image(s) as "${result.label}".`);
      queryClient.invalidateQueries({ queryKey: ["gallery"] });
      queryClient.invalidateQueries({ queryKey: ["label-options"] });
    },
  });

  const unlabelMutation = useMutation({
    mutationFn: (label: string) => removeLabel([...selected], label),
    onSuccess: (result) => {
      toast.success(`Removed "${result.label}" from ${result.removed} image(s).`);
      queryClient.invalidateQueries({ queryKey: ["gallery"] });
      queryClient.invalidateQueries({ queryKey: ["label-options"] });
    },
  });

  // One export action driven by a scope: the current filters/search, the whole
  // dataset, or just the checked selection.
  const exportMutation = useMutation({
    mutationFn: ({ scope, format, purpose }: {
      scope: ExportScope;
      format: ExportFormat;
      purpose: ExportPurpose;
    }) => {
      if (scope === "selected") return downloadExportSelected([...selected], format, purpose);
      if (scope === "all") return downloadExportFiltered({}, format, purpose);
      return downloadExportFiltered(
        {
          q: params.q,
          dataset: params.dataset,
          split: params.split,
          length: params.length,
          orientation: params.orientation,
          min_agreement: params.min_agreement,
          status: params.status,
          labels: params.labels,
          search_mode: params.search_mode,
        },
        format,
        purpose,
      );
    },
    onSuccess: () => toast.success("Export downloaded."),
  });

  const isTagging = tagMutation.isPending || untagMutation.isPending;

  // Endless scroll: load the next page when the sentinel nears the bottom.
  // The scroll container differs by layout: on desktop the grid scrolls inside
  // its own area; on mobile the whole page scrolls. Using the wrong root (an
  // element that isn't actually scrolling) makes the sentinel permanently
  // intersect and fetches in a loop, so we pick the root per breakpoint.
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return;

    const mql = window.matchMedia("(max-width: 820px)");
    let observer: IntersectionObserver | null = null;

    const setup = () => {
      observer?.disconnect();
      const root = mql.matches ? null : scrollRef.current;
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
            fetchNextPage();
          }
        },
        { root, rootMargin: "600px" },
      );
      observer.observe(node);
    };

    setup();
    mql.addEventListener("change", setup);
    return () => {
      observer?.disconnect();
      mql.removeEventListener("change", setup);
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <div className={styles.layout}>
      <section className={styles.gallery}>
        <div className={styles.stickyBar}>
          <div className={styles.galleryHeader}>
            <div className={styles.search}>
              <SearchBar
                value={filters.q}
                onSearch={(query) => setFilter("q", query)}
                mode={searchMode}
                onModeChange={(mode) =>
                  setFilter("search_mode", mode === "meaning" ? "meaning" : "")
                }
              />
            </div>
            <div className={styles.headerRight}>
              <span className={styles.count}>
                {items.length.toLocaleString()} / {total.toLocaleString()} images
              </span>
              <Button variant="secondary" onClick={() => setShowBulk(true)}>
                Bulk tag
              </Button>
            </div>
          </div>

          <GalleryToolbar
            selectedCount={selected.size}
            isBusy={isTagging}
            onSelectAll={selectAll}
            onClear={clearSelection}
            onPass={() => tagMutation.mutate("passed")}
            onFail={() => tagMutation.mutate("failed")}
            onRemove={() => untagMutation.mutate()}
            onAddLabel={(label) => labelMutation.mutate(label)}
            onRemoveLabel={(label) => unlabelMutation.mutate(label)}
            onExport={(scope, format, purpose) =>
              exportMutation.mutate({ scope, format, purpose })
            }
          />
        </div>

        <div className={styles.scrollArea} ref={scrollRef}>
          {meaningWithoutQuery ? (
            <div className={styles.state}>
              Type a phrase above to search images by meaning (e.g. &ldquo;a child
              playing in water&rdquo;).
            </div>
          ) : isLoading ? (
            <div className={styles.state}>
              <Spinner /> Loading gallery…
            </div>
          ) : indexBuilding ? (
            <div className={styles.state}>
              <Spinner /> Building the semantic search index… this runs once and
              can take a few minutes. Try again shortly.
            </div>
          ) : isError ? (
            <div className={styles.error}>Couldn&apos;t load the gallery.</div>
          ) : items.length === 0 ? (
            <div className={styles.state}>No images found.</div>
          ) : (
            <>
              <ImageGrid items={items} selected={selected} onToggleSelect={toggleSelect} />
              <div ref={sentinelRef} className={styles.sentinel} aria-hidden />
              {isFetchingNextPage && (
                <div className={styles.loadMore}>
                  <Spinner /> Loading more…
                </div>
              )}
              {!hasNextPage && (
                <div className={styles.loadMore}>You&apos;ve reached the end.</div>
              )}
            </>
          )}
        </div>
      </section>

      <aside className={styles.filters}>
        <FiltersPanel
          filters={filters}
          options={options}
          labelOptions={labelOptions?.labels ?? []}
          selectedLabels={selectedLabels}
          hasActiveFilters={hasActiveFilters}
          onChange={setFilter}
          onToggleLabel={toggleLabel}
          onClear={clearFilters}
        />
      </aside>

      {showBulk && (
        <BulkTagModal
          onClose={() => setShowBulk(false)}
          onApplied={() => {
            queryClient.invalidateQueries({ queryKey: ["gallery"] });
            queryClient.invalidateQueries({ queryKey: ["label-options"] });
          }}
        />
      )}
    </div>
  );
}
