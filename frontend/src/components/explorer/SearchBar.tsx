import { useEffect, useRef, useState } from "react";

import type { SearchMode } from "../../api/tags";
import styles from "./css/SearchBar.module.css";

const DEBOUNCE_MS = 350;

interface SearchBarProps {
  value: string;
  onSearch: (query: string) => void;
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
}

const MODE_COPY: Record<SearchMode, { label: string; placeholder: string }> = {
  keyword: {
    label: "Search captions",
    placeholder: "e.g. a dog running on the beach",
  },
  meaning: {
    label: "Search by meaning",
    placeholder: "e.g. a child playing happily in water",
  },
};

function SearchIcon() {
  return (
    <svg
      className={styles.icon}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

const MODES: { value: SearchMode; label: string }[] = [
  { value: "keyword", label: "Keyword" },
  { value: "meaning", label: "Meaning" },
];

// Debounced text search. Keeps a local value for snappy typing and only pushes
// the committed query upward (to the URL) after the user pauses. A mode toggle
// switches between caption keyword search and CLIP semantic ("meaning") search.
export default function SearchBar({ value, onSearch, mode, onModeChange }: SearchBarProps) {
  const [text, setText] = useState(value);
  const timer = useRef<number | undefined>(undefined);

  // Sync when the URL value changes from outside (e.g. "Clear filters").
  useEffect(() => {
    setText(value);
  }, [value]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  function handleChange(next: string) {
    setText(next);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => onSearch(next), DEBOUNCE_MS);
  }

  const copy = MODE_COPY[mode];

  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <label className={styles.label} htmlFor="gallery-search">
          {copy.label}
        </label>
        <div className={styles.modes} role="group" aria-label="Search mode">
          {MODES.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`${styles.mode} ${option.value === mode ? styles.modeActive : ""}`}
              aria-pressed={option.value === mode}
              onClick={() => onModeChange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.wrap}>
        <SearchIcon />
        <input
          id="gallery-search"
          type="search"
          className={styles.input}
          placeholder={copy.placeholder}
          value={text}
          onChange={(event) => handleChange(event.target.value)}
        />
      </div>
      {mode === "meaning" && (
        <p className={styles.hint}>
          Type to search by visual meaning; leave empty to browse all images.
        </p>
      )}
    </div>
  );
}
