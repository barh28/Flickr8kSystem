import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { getFile } from "../api/files";
import {
  addLabel,
  getLabelOptions,
  getLabels,
  getTagStatus,
  removeLabel,
  removeTags,
  setTags,
} from "../api/tags";
import Button from "../components/common/Button";
import Spinner from "../components/common/Spinner";
import { imageSrc } from "../config";
import { toast } from "../toast/toastStore";
import type { TagStatus } from "../types";
import styles from "./css/ImageDetailPage.module.css";

interface DetailState {
  ids?: string[];
  backTo?: string;
}

export default function ImageDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const state = (location.state as DetailState | null) ?? {};
  // Memoize so the navigation callbacks/effect don't re-run every render.
  const ids = useMemo(() => state.ids ?? [], [state.ids]);
  const backTo = state.backTo ?? "/";

  const index = ids.indexOf(id);
  const prevId = index > 0 ? ids[index - 1] : undefined;
  const nextId = index >= 0 && index < ids.length - 1 ? ids[index + 1] : undefined;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["file", id],
    queryFn: () => getFile(id),
    enabled: id !== "",
  });

  const queryClient = useQueryClient();
  const { data: tagData } = useQuery({
    queryKey: ["tag-status", id],
    queryFn: () => getTagStatus(id),
    enabled: id !== "",
    retry: false,
    // A missing/failed status lookup should silently fall back to "Untagged".
    meta: { suppressErrorToast: true },
  });
  const tagStatus = tagData?.status ?? null;

  function onTagChanged() {
    queryClient.invalidateQueries({ queryKey: ["tag-status", id] });
    queryClient.invalidateQueries({ queryKey: ["gallery"] });
  }

  const tagMutation = useMutation({
    mutationFn: (status: TagStatus) => setTags([id], status),
    onSuccess: (_result, status) => {
      toast.success(`Tagged as ${status}.`);
      onTagChanged();
    },
  });

  const untagMutation = useMutation({
    mutationFn: () => removeTags([id]),
    onSuccess: () => {
      toast.success("Tag removed.");
      onTagChanged();
    },
  });

  const isTagging = tagMutation.isPending || untagMutation.isPending;

  // Free-form labels for this image.
  const { data: labelData } = useQuery({
    queryKey: ["labels", id],
    queryFn: () => getLabels(id),
    enabled: id !== "",
    retry: false,
    meta: { suppressErrorToast: true },
  });
  const labels = labelData?.labels ?? [];

  const { data: labelOptions } = useQuery({
    queryKey: ["label-options"],
    queryFn: getLabelOptions,
  });

  const [labelDraft, setLabelDraft] = useState("");

  function onLabelsChanged() {
    queryClient.invalidateQueries({ queryKey: ["labels", id] });
    queryClient.invalidateQueries({ queryKey: ["label-options"] });
    queryClient.invalidateQueries({ queryKey: ["gallery"] });
  }

  const addLabelMutation = useMutation({
    mutationFn: (label: string) => addLabel([id], label),
    onSuccess: (result) => {
      toast.success(`Labeled "${result.label}".`);
      setLabelDraft("");
      onLabelsChanged();
    },
  });

  const removeLabelMutation = useMutation({
    mutationFn: (label: string) => removeLabel([id], label),
    onSuccess: () => onLabelsChanged(),
  });

  const isLabeling = addLabelMutation.isPending || removeLabelMutation.isPending;

  function submitLabel() {
    const value = labelDraft.trim();
    if (value) addLabelMutation.mutate(value);
  }

  const goTo = useCallback(
    (targetId: string) => {
      navigate(`/image/${targetId}`, { state: { ids, backTo }, replace: true });
    },
    [navigate, ids, backTo],
  );

  const goBack = useCallback(() => navigate(backTo), [navigate, backTo]);

  // Keyboard navigation: ←/→ between neighbours, Esc back to results.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "ArrowLeft" && prevId) goTo(prevId);
      else if (event.key === "ArrowRight" && nextId) goTo(nextId);
      else if (event.key === "Escape") goBack();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [prevId, nextId, goTo, goBack]);

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <Button variant="secondary" onClick={goBack}>
          ← Back to results
        </Button>
        <div className={styles.nav}>
          <Button variant="secondary" disabled={!prevId} onClick={() => prevId && goTo(prevId)}>
            ← Prev
          </Button>
          {index >= 0 && (
            <span className={styles.position}>
              {index + 1} of {ids.length}
            </span>
          )}
          <Button variant="secondary" disabled={!nextId} onClick={() => nextId && goTo(nextId)}>
            Next →
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className={styles.state}>
          <Spinner /> Loading image…
        </div>
      ) : isError || !data ? (
        <div className={styles.state}>Couldn&apos;t load this image.</div>
      ) : (
        <div className={styles.content}>
          <div className={styles.imageWrap}>
            <img
              className={styles.image}
              src={imageSrc(data.image_url)}
              alt={data.captions[0] ?? data.id}
            />
          </div>

          <div className={styles.panel}>
            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Your tag</h3>
              <div className={styles.tagRow}>
                <span
                  className={`${styles.tagBadge} ${
                    tagStatus === "passed"
                      ? styles.passed
                      : tagStatus === "failed"
                        ? styles.failed
                        : ""
                  }`}
                >
                  {tagStatus ?? "Untagged"}
                </span>
                <div className={styles.tagActions}>
                  <button
                    type="button"
                    className={`${styles.tagBtn} ${styles.pass} ${tagStatus === "passed" ? styles.activePass : ""}`}
                    onClick={() => tagMutation.mutate("passed")}
                    disabled={isTagging}
                  >
                    Passed
                  </button>
                  <button
                    type="button"
                    className={`${styles.tagBtn} ${styles.fail} ${tagStatus === "failed" ? styles.activeFail : ""}`}
                    onClick={() => tagMutation.mutate("failed")}
                    disabled={isTagging}
                  >
                    Failed
                  </button>
                  <button
                    type="button"
                    className={styles.tagBtn}
                    onClick={() => untagMutation.mutate()}
                    disabled={isTagging || !tagStatus}
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Your labels</h3>
              <div className={styles.labelChips}>
                {labels.length === 0 && <span className={styles.muted}>No labels yet</span>}
                {labels.map((label) => (
                  <span key={label} className={styles.labelChip}>
                    {label}
                    <button
                      type="button"
                      className={styles.labelRemove}
                      aria-label={`Remove label ${label}`}
                      disabled={isLabeling}
                      onClick={() => removeLabelMutation.mutate(label)}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className={styles.labelAdd}>
                <input
                  className={styles.labelInput}
                  type="text"
                  list="label-suggestions"
                  value={labelDraft}
                  maxLength={50}
                  placeholder="Add a label (e.g. dogs)…"
                  disabled={isLabeling}
                  onChange={(event) => setLabelDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") submitLabel();
                  }}
                />
                <datalist id="label-suggestions">
                  {(labelOptions?.labels ?? []).map((option) => (
                    <option key={option.label} value={option.label} />
                  ))}
                </datalist>
                <Button
                  variant="secondary"
                  onClick={submitLabel}
                  disabled={isLabeling || labelDraft.trim() === ""}
                >
                  Add
                </Button>
              </div>
            </div>

            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Metadata</h3>
              <div className={styles.meta}>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Dataset</span>
                  <span className={styles.metaValue}>{data.dataset}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Split</span>
                  <span className={styles.metaValue}>{data.split}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Dimensions</span>
                  <span className={styles.metaValue}>
                    {data.width} × {data.height}
                  </span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Orientation</span>
                  <span className={styles.metaValue}>{data.orientation}</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Caption length</span>
                  <span className={styles.metaValue}>{data.caption_length} words (avg)</span>
                </div>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Agreement</span>
                  <span className={styles.metaValue}>{Math.round(data.agreement * 100)}%</span>
                </div>
              </div>
            </div>

            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Captions ({data.captions.length})</h3>
              <ul className={styles.captions}>
                {data.captions.map((caption, i) => (
                  <li key={i} className={styles.caption}>
                    {caption}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
