import styles from "./css/SegmentedControl.module.css";

export interface Segment {
  value: string;
  label: string;
}

interface SegmentedControlProps {
  label: string;
  options: Segment[];
  value: string;
  onChange: (value: string) => void;
}

export default function SegmentedControl({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps) {
  return (
    <div className={styles.group}>
      <span className={styles.label}>{label}</span>
      <div className={styles.segments} role="group" aria-label={label}>
        {options.map((option) => {
          const active = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              className={`${styles.segment} ${active ? styles.active : ""}`}
              aria-pressed={active}
              onClick={() => onChange(option.value)}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
