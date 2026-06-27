import { useEffect, useRef, useState } from "react";

import styles from "./css/SearchBar.module.css";

const DEBOUNCE_MS = 350;

interface SearchBarProps {
  value: string;
  onSearch: (query: string) => void;
}

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

// Debounced text search. Keeps a local value for snappy typing and only pushes
// the committed query upward (to the URL) after the user pauses.
export default function SearchBar({ value, onSearch }: SearchBarProps) {
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

  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor="gallery-search">
        Search captions
      </label>
      <div className={styles.wrap}>
        <SearchIcon />
        <input
          id="gallery-search"
          type="search"
          className={styles.input}
          placeholder="e.g. a dog running on the beach"
          value={text}
          onChange={(event) => handleChange(event.target.value)}
        />
      </div>
    </div>
  );
}
