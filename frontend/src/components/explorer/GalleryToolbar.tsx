import { useState } from "react";

import styles from "./css/GalleryToolbar.module.css";

export type ExportFormat = "json" | "jsonl" | "csv";
export type ExportScope = "filtered" | "all" | "selected";
export type ExportPurpose = "report" | "training";

interface GalleryToolbarProps {
  selectedCount: number;
  isBusy: boolean;
  onSelectAll: () => void;
  onClear: () => void;
  onPass: () => void;
  onFail: () => void;
  onRemove: () => void;
  onAddLabel: (label: string) => void;
  onRemoveLabel: (label: string) => void;
  onExport: (scope: ExportScope, format: ExportFormat, purpose: ExportPurpose) => void;
}

const SCOPES: { value: ExportScope; label: string; hint: string }[] = [
  { value: "filtered", label: "Filtered", hint: "Everything matching the current search & filters" },
  { value: "all", label: "Everything", hint: "The whole dataset, ignoring filters" },
  { value: "selected", label: "Selected", hint: "Only the images you have checked" },
];

const PURPOSES: { value: ExportPurpose; label: string; hint: string }[] = [
  {
    value: "report",
    label: "Report",
    hint: "Annotation file with your pass/fail + labels (re-importable via Bulk tag)",
  },
  {
    value: "training",
    label: "Training",
    hint: "ML-ready manifest: image + captions only (status & labels stripped)",
  },
];

// Each purpose offers the formats that make sense for it.
const FORMATS: Record<ExportPurpose, { value: ExportFormat; label: string }[]> = {
  report: [
    { value: "json", label: "JSON" },
    { value: "csv", label: "CSV" },
  ],
  training: [
    { value: "jsonl", label: "JSONL" },
    { value: "csv", label: "CSV" },
  ],
};

export default function GalleryToolbar({
  selectedCount,
  isBusy,
  onSelectAll,
  onClear,
  onPass,
  onFail,
  onRemove,
  onAddLabel,
  onRemoveLabel,
  onExport,
}: GalleryToolbarProps) {
  const [purpose, setPurpose] = useState<ExportPurpose>("report");
  const [format, setFormat] = useState<ExportFormat>("json");
  const [scope, setScope] = useState<ExportScope>("filtered");
  const [labelDraft, setLabelDraft] = useState("");

  function changePurpose(next: ExportPurpose) {
    setPurpose(next);
    // Keep CSV across both; otherwise snap to the purpose's default format.
    if (format !== "csv") setFormat(FORMATS[next][0].value);
  }
  const hasSelection = selectedCount > 0;
  const tagDisabled = !hasSelection || isBusy;
  const labelDisabled = tagDisabled || labelDraft.trim() === "";
  const exportDisabled = isBusy || (scope === "selected" && !hasSelection);

  function submitLabel() {
    const value = labelDraft.trim();
    if (!value || !hasSelection) return;
    onAddLabel(value);
    setLabelDraft("");
  }

  function submitRemoveLabel() {
    const value = labelDraft.trim();
    if (!value || !hasSelection) return;
    onRemoveLabel(value);
    setLabelDraft("");
  }

  return (
    <div className={styles.toolbar}>
      <div className={styles.group}>
        <span className={styles.info} title="Select images to tag or export">
          <span className={styles.count}>{selectedCount}</span> selected
        </span>
        <button type="button" className={styles.btn} onClick={onSelectAll}>
          Select all
        </button>
        <button type="button" className={styles.btn} onClick={onClear} disabled={!hasSelection}>
          Clear
        </button>
        <span className={styles.divider} />
        <button
          type="button"
          className={`${styles.btn} ${styles.pass}`}
          onClick={onPass}
          disabled={tagDisabled}
        >
          Mark passed
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.fail}`}
          onClick={onFail}
          disabled={tagDisabled}
        >
          Mark failed
        </button>
        <button type="button" className={styles.btn} onClick={onRemove} disabled={tagDisabled}>
          Remove tag
        </button>
        <span className={styles.divider} />
        <input
          className={styles.labelInput}
          type="text"
          value={labelDraft}
          maxLength={50}
          placeholder="Label…"
          disabled={!hasSelection || isBusy}
          onChange={(event) => setLabelDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submitLabel();
          }}
        />
        <button
          type="button"
          className={styles.btn}
          onClick={submitLabel}
          disabled={labelDisabled}
        >
          Add
        </button>
        <button
          type="button"
          className={styles.btn}
          onClick={submitRemoveLabel}
          disabled={labelDisabled}
          title="Remove this label from the selected images"
        >
          Remove
        </button>
      </div>

      <div className={styles.group}>
        <span className={styles.info}>Export</span>
        <div className={styles.toggle} role="group" aria-label="Export purpose">
          {PURPOSES.map((item) => (
            <button
              key={item.value}
              type="button"
              title={item.hint}
              className={`${styles.toggleBtn} ${purpose === item.value ? styles.toggleActive : ""}`}
              onClick={() => changePurpose(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className={styles.toggle} role="group" aria-label="Export scope">
          {SCOPES.map((item) => (
            <button
              key={item.value}
              type="button"
              title={item.hint}
              className={`${styles.toggleBtn} ${scope === item.value ? styles.toggleActive : ""}`}
              onClick={() => setScope(item.value)}
            >
              {item.value === "selected" && hasSelection ? `${item.label} (${selectedCount})` : item.label}
            </button>
          ))}
        </div>
        <div className={styles.toggle} role="group" aria-label="Export format">
          {FORMATS[purpose].map((item) => (
            <button
              key={item.value}
              type="button"
              className={`${styles.toggleBtn} ${format === item.value ? styles.toggleActive : ""}`}
              onClick={() => setFormat(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={`${styles.btn} ${styles.primary}`}
          onClick={() => onExport(scope, format, purpose)}
          disabled={exportDisabled}
        >
          Export
        </button>
      </div>
    </div>
  );
}
