import type { MouseEvent } from "react";
import { Link } from "react-router-dom";

import { imageSrc } from "../../config";
import type { FileItem } from "../../types";
import styles from "./css/ImageCard.module.css";

interface ImageCardProps {
  item: FileItem;
  // The current list's ids + the gallery URL, so the detail view can offer
  // prev/next navigation and a "back to results" that preserves filters.
  ids: string[];
  backTo: string;
  selected: boolean;
  onToggleSelect: (id: string) => void;
}

function CheckIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default function ImageCard({
  item,
  ids,
  backTo,
  selected,
  onToggleSelect,
}: ImageCardProps) {
  const caption = item.captions.length > 0 ? item.captions[0] : "No caption";

  function handleSelect(event: MouseEvent) {
    // Keep the click from following the card link / bubbling to it.
    event.preventDefault();
    event.stopPropagation();
    onToggleSelect(item.id);
  }

  return (
    <Link
      to={`/image/${item.id}`}
      state={{ ids, backTo }}
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      aria-label={`Open image: ${caption}`}
    >
      <button
        type="button"
        className={`${styles.checkbox} ${selected ? styles.checked : ""}`}
        onClick={handleSelect}
        aria-label={selected ? "Deselect image" : "Select image"}
        aria-pressed={selected}
      >
        {selected && <CheckIcon />}
      </button>
      <img
        className={styles.thumb}
        src={imageSrc(item.image_url)}
        alt={caption}
        loading="lazy"
      />
      <div className={styles.body}>
        <p className={styles.caption}>{caption}</p>
        <div className={styles.meta}>
          <span className={styles.chip}>{item.split}</span>
          <span className={styles.chip}>{item.orientation}</span>
          {item.tag_status && (
            <span
              className={`${styles.chip} ${
                item.tag_status === "passed" ? styles.passed : styles.failed
              }`}
            >
              {item.tag_status}
            </span>
          )}
          {item.labels?.map((label) => (
            <span key={label} className={`${styles.chip} ${styles.label}`}>
              {label}
            </span>
          ))}
        </div>
      </div>
    </Link>
  );
}
