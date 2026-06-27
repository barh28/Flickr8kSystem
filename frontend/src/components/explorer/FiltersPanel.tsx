import { useState } from "react";

import type { LabelOption, OptionsResponse } from "../../types";
import Button from "../common/Button";
import SegmentedControl from "../common/SegmentedControl";
import type { Segment } from "../common/SegmentedControl";
import Select from "../common/Select";
import type { SelectOption } from "../common/Select";
import Slider from "../common/Slider";
import styles from "./css/FiltersPanel.module.css";

// All filter values the gallery understands, kept as plain strings ("" = unset)
// so they map cleanly onto URL search params. Keys match the URL param names.
export interface GalleryFilters {
  q: string;
  dataset: string;
  split: string;
  length: string;
  orientation: string;
  min_agreement: string;
  status: string;
  sort: string;
}

const LENGTH_OPTIONS: Segment[] = [
  { value: "", label: "Any" },
  { value: "short", label: "Short" },
  { value: "medium", label: "Medium" },
  { value: "long", label: "Long" },
];

const ORIENTATION_OPTIONS: Segment[] = [
  { value: "", label: "All" },
  { value: "landscape", label: "Landscape" },
  { value: "portrait", label: "Portrait" },
  { value: "square", label: "Square" },
];

const STATUS_OPTIONS: Segment[] = [
  { value: "", label: "All" },
  { value: "passed", label: "Passed" },
  { value: "failed", label: "Failed" },
];

const SORT_OPTIONS: SelectOption[] = [
  { value: "id", label: "Default" },
  { value: "length", label: "Caption length" },
  { value: "agreement", label: "Agreement" },
  { value: "random", label: "Random" },
];

function toOptions(values: string[] | undefined): SelectOption[] {
  return (values ?? []).map((value) => ({ value, label: value }));
}

interface FiltersPanelProps {
  filters: GalleryFilters;
  options?: OptionsResponse;
  labelOptions: LabelOption[];
  selectedLabels: string[];
  hasActiveFilters: boolean;
  onChange: (key: keyof GalleryFilters, value: string) => void;
  onToggleLabel: (label: string) => void;
  onClear: () => void;
}

export default function FiltersPanel({
  filters,
  options,
  labelOptions,
  selectedLabels,
  hasActiveFilters,
  onChange,
  onToggleLabel,
  onClear,
}: FiltersPanelProps) {
  // The slider works in whole percent; the URL stores a 0..1 fraction.
  const agreementPct = filters.min_agreement
    ? Math.round(Number(filters.min_agreement) * 100)
    : 0;

  // Keep the label list compact; collapse past a threshold behind "Show more".
  const LABELS_COLLAPSED_COUNT = 8;
  const [labelsExpanded, setLabelsExpanded] = useState(false);
  const labelsOverflow = labelOptions.length > LABELS_COLLAPSED_COUNT;
  const visibleLabels =
    labelsExpanded || !labelsOverflow
      ? labelOptions
      : labelOptions.slice(0, LABELS_COLLAPSED_COUNT);

  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>Filters</h2>

      {options && options.datasets.length > 1 && (
        <Select
          label="Dataset"
          placeholder="All datasets"
          value={filters.dataset}
          options={toOptions(options.datasets)}
          onChange={(event) => onChange("dataset", event.target.value)}
        />
      )}

      <Select
        label="Split"
        placeholder="All splits"
        value={filters.split}
        options={toOptions(options?.splits)}
        onChange={(event) => onChange("split", event.target.value)}
      />

      <SegmentedControl
        label="Orientation"
        options={ORIENTATION_OPTIONS}
        value={filters.orientation}
        onChange={(value) => onChange("orientation", value)}
      />

      <SegmentedControl
        label="Caption length"
        options={LENGTH_OPTIONS}
        value={filters.length}
        onChange={(value) => onChange("length", value)}
      />

      <SegmentedControl
        label="Tag status"
        options={STATUS_OPTIONS}
        value={filters.status}
        onChange={(value) => onChange("status", value)}
      />

      {labelOptions.length > 0 && (
        <div className={styles.labels}>
          <span className={styles.labelsTitle}>My labels</span>
          <div className={styles.chips}>
            {visibleLabels.map((option) => {
              const active = selectedLabels.includes(option.label);
              return (
                <button
                  key={option.label}
                  type="button"
                  className={`${styles.chip} ${active ? styles.chipActive : ""}`}
                  onClick={() => onToggleLabel(option.label)}
                  aria-pressed={active}
                >
                  {option.label}
                  <span className={styles.chipCount}>{option.count}</span>
                </button>
              );
            })}
          </div>
          {labelsOverflow && (
            <button
              type="button"
              className={styles.showMore}
              onClick={() => setLabelsExpanded((value) => !value)}
            >
              {labelsExpanded
                ? "Show less"
                : `Show more (${labelOptions.length - LABELS_COLLAPSED_COUNT})`}
            </button>
          )}
        </div>
      )}

      <Slider
        label="Min. agreement"
        value={agreementPct}
        min={0}
        max={100}
        step={5}
        formatValue={(value) => (value === 0 ? "Any" : `≥ ${value}%`)}
        onChange={(value) => onChange("min_agreement", value > 0 ? String(value / 100) : "")}
      />

      <Select
        label="Sort by"
        value={filters.sort}
        options={SORT_OPTIONS}
        onChange={(event) => onChange("sort", event.target.value)}
      />

      <div className={styles.clear}>
        <Button variant="ghost" block onClick={onClear} disabled={!hasActiveFilters}>
          Clear filters
        </Button>
      </div>
    </div>
  );
}
