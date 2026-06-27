import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { DragEvent } from "react";

import { addLabel, setTags } from "../../api/tags";
import { toast } from "../../toast/toastStore";
import { parseBulkFile } from "../../utils/bulk";
import type { BulkParseResult, BulkStatus } from "../../utils/bulk";
import Button from "../common/Button";
import SegmentedControl from "../common/SegmentedControl";
import type { Segment } from "../common/SegmentedControl";
import styles from "./css/BulkTagModal.module.css";

const STATUS_OPTIONS: Segment[] = [
  { value: "passed", label: "Passed" },
  { value: "failed", label: "Failed" },
];

interface BulkTagModalProps {
  onClose: () => void;
  onApplied: () => void;
}

// One-line example files so users don't have to guess the format. The `status`
// and `label` fields are optional (drop them to just apply one chosen value).
const TEMPLATES: Record<string, { filename: string; mime: string; content: string }> = {
  csv: {
    filename: "bulk-tags-example.csv",
    mime: "text/csv",
    content: "id,status,label\n0a1b2c3d4e5f6.jpg,failed,dogs\n",
  },
  json: {
    filename: "bulk-tags-example.json",
    mime: "application/json",
    content:
      JSON.stringify([{ id: "0a1b2c3d4e5f6.jpg", status: "failed", label: "dogs" }], null, 2) +
      "\n",
  },
  txt: {
    filename: "bulk-tags-example.txt",
    mime: "text/plain",
    // No header: columns are positional -> id, status, label (one row per line).
    content: "0a1b2c3d4e5f6.jpg,failed,dogs\n",
  },
};

function downloadTemplate(kind: keyof typeof TEMPLATES) {
  const { filename, mime, content } = TEMPLATES[kind];
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function BulkTagModal({ onClose, onApplied }: BulkTagModalProps) {
  const [fileName, setFileName] = useState("");
  const [parsed, setParsed] = useState<BulkParseResult | null>(null);
  const [parseError, setParseError] = useState("");
  const [dragging, setDragging] = useState(false);

  // Status and label are two independent actions; either or both can run in one
  // pass. Each can take its value per-row from the file or one chosen value.
  const [applyStatus, setApplyStatus] = useState(false);
  const [statusFromFile, setStatusFromFile] = useState(false);
  const [statusValue, setStatusValue] = useState<BulkStatus>("passed");

  const [applyLabel, setApplyLabel] = useState(false);
  const [labelFromFile, setLabelFromFile] = useState(false);
  const [labelValue, setLabelValue] = useState("");

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setFileName(file.name);
    setParseError("");
    try {
      const result = parseBulkFile(await file.text(), file.name);
      if (result.rows.length === 0) {
        setParsed(null);
        setParseError("No image IDs found in this file.");
        return;
      }
      setParsed(result);
      // Default to applying whatever the file carries (from its own rows). If it
      // carries neither, default to applying a chosen status so there's an action.
      setApplyStatus(result.hasStatus || (!result.hasStatus && !result.hasLabel));
      setStatusFromFile(result.hasStatus);
      setApplyLabel(result.hasLabel);
      setLabelFromFile(result.hasLabel);
    } catch {
      setParsed(null);
      setParseError("Couldn't read this file. Use CSV, JSON, or TXT with image IDs.");
    }
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files?.[0]);
  }

  const applyMutation = useMutation({
    mutationFn: async () => {
      const empty = { statusCount: 0, labelCount: 0, missing: 0 };
      if (!parsed) return empty;
      const rows = parsed.rows;
      const allIds = rows.map((row) => row.id);
      const missing = new Set<string>();
      let statusCount = 0;
      let labelCount = 0;

      if (applyStatus) {
        if (statusFromFile) {
          for (const status of ["passed", "failed"] as BulkStatus[]) {
            const ids = rows.filter((row) => row.status === status).map((row) => row.id);
            if (ids.length === 0) continue;
            const result = await setTags(ids, status);
            statusCount += result.tagged;
            result.skipped_missing.forEach((id) => missing.add(id));
          }
        } else {
          const result = await setTags(allIds, statusValue);
          statusCount += result.tagged;
          result.skipped_missing.forEach((id) => missing.add(id));
        }
      }

      if (applyLabel) {
        if (labelFromFile) {
          const byLabel = new Map<string, string[]>();
          for (const row of rows) {
            for (const label of row.labels ?? []) {
              const ids = byLabel.get(label) ?? [];
              ids.push(row.id);
              byLabel.set(label, ids);
            }
          }
          for (const [label, ids] of byLabel) {
            const result = await addLabel(ids, label);
            labelCount += result.labeled;
            result.skipped_missing.forEach((id) => missing.add(id));
          }
        } else {
          const result = await addLabel(allIds, labelValue.trim());
          labelCount += result.labeled;
          result.skipped_missing.forEach((id) => missing.add(id));
        }
      }

      return { statusCount, labelCount, missing: missing.size };
    },
    onSuccess: ({ statusCount, labelCount, missing }) => {
      const parts: string[] = [];
      if (applyStatus) parts.push(`status on ${statusCount}`);
      if (applyLabel) parts.push(`labels on ${labelCount}`);
      toast.success(
        `Applied ${parts.join(" · ")} image(s)` +
          (missing > 0 ? ` · ${missing} unknown ID(s) skipped` : ""),
      );
      onApplied();
      onClose();
    },
  });

  const statusValid = !applyStatus || !statusFromFile || (parsed?.hasStatus ?? false);
  const labelValid =
    !applyLabel || (labelFromFile ? (parsed?.hasLabel ?? false) : labelValue.trim() !== "");
  const canApply =
    !!parsed &&
    !applyMutation.isPending &&
    (applyStatus || applyLabel) &&
    statusValid &&
    labelValid;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-label="Bulk tag from file"
        onClick={(event) => event.stopPropagation()}
      >
        <header className={styles.header}>
          <h2 className={styles.title}>Bulk tag from file</h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <p className={styles.hint}>
          Upload a <strong>CSV</strong>, <strong>JSON</strong>, or <strong>TXT</strong> file of
          image IDs (e.g. the ones your model passed or failed on). Optional <code>status</code>{" "}
          and <code>label</code> columns/fields are supported.
        </p>

        <div className={styles.templates}>
          <span className={styles.templatesLabel}>Need a template?</span>
          <button type="button" className={styles.templateLink} onClick={() => downloadTemplate("csv")}>
            CSV
          </button>
          <button type="button" className={styles.templateLink} onClick={() => downloadTemplate("json")}>
            JSON
          </button>
          <button type="button" className={styles.templateLink} onClick={() => downloadTemplate("txt")}>
            TXT
          </button>
        </div>

        <label
          className={`${styles.drop} ${dragging ? styles.dropActive : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <input
            type="file"
            accept=".csv,.json,.txt,text/csv,application/json,text/plain"
            className={styles.fileInput}
            onChange={(event) => handleFile(event.target.files?.[0])}
          />
          <span className={styles.dropText}>
            {fileName ? fileName : "Drag & drop a file here, or click to choose…"}
          </span>
        </label>

        {parseError && <div className={styles.error}>{parseError}</div>}

        {parsed && (
          <div className={styles.summary}>
            Found <strong>{parsed.rows.length.toLocaleString()}</strong> image ID(s)
            {parsed.hasStatus && " · includes status"}
            {parsed.hasLabel && " · includes labels"}
          </div>
        )}

        {parsed && (
          <div className={styles.controls}>
            <p className={styles.controlsHint}>
              Choose what to apply — you can do both at once.
            </p>

            <section className={styles.action}>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={applyStatus}
                  onChange={(event) => setApplyStatus(event.target.checked)}
                />
                <strong>Set status</strong>
              </label>
              {applyStatus && (
                <div className={styles.actionBody}>
                  {!statusFromFile && (
                    <SegmentedControl
                      label="Status to apply"
                      options={STATUS_OPTIONS}
                      value={statusValue}
                      onChange={(value) => setStatusValue(value as BulkStatus)}
                    />
                  )}
                  <label className={styles.check}>
                    <input
                      type="checkbox"
                      checked={statusFromFile}
                      disabled={!parsed.hasStatus}
                      onChange={(event) => setStatusFromFile(event.target.checked)}
                    />
                    Use each row&apos;s status from the file
                    {!parsed.hasStatus && (
                      <span className={styles.muted}> (no status column found)</span>
                    )}
                  </label>
                </div>
              )}
            </section>

            <section className={styles.action}>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={applyLabel}
                  onChange={(event) => setApplyLabel(event.target.checked)}
                />
                <strong>Add label</strong>
              </label>
              {applyLabel && (
                <div className={styles.actionBody}>
                  {!labelFromFile && (
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Label to apply</span>
                      <input
                        type="text"
                        className={styles.textInput}
                        value={labelValue}
                        maxLength={50}
                        placeholder="e.g. dogs"
                        onChange={(event) => setLabelValue(event.target.value)}
                      />
                    </label>
                  )}
                  <label className={styles.check}>
                    <input
                      type="checkbox"
                      checked={labelFromFile}
                      disabled={!parsed.hasLabel}
                      onChange={(event) => setLabelFromFile(event.target.checked)}
                    />
                    Use each row&apos;s label from the file
                    {!parsed.hasLabel && (
                      <span className={styles.muted}> (no label column found)</span>
                    )}
                  </label>
                </div>
              )}
            </section>
          </div>
        )}

        <footer className={styles.footer}>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => applyMutation.mutate()} disabled={!canApply}>
            {applyMutation.isPending ? "Applying…" : "Apply"}
          </Button>
        </footer>
      </div>
    </div>
  );
}
