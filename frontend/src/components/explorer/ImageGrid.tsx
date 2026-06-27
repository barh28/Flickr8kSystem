import { useLocation } from "react-router-dom";

import type { FileItem } from "../../types";
import ImageCard from "./ImageCard";
import styles from "./css/ImageGrid.module.css";

interface ImageGridProps {
  items: FileItem[];
  selected: Set<string>;
  onToggleSelect: (id: string) => void;
}

export default function ImageGrid({ items, selected, onToggleSelect }: ImageGridProps) {
  const location = useLocation();
  const backTo = `${location.pathname}${location.search}`;
  const ids = items.map((item) => item.id);

  return (
    <div className={styles.grid}>
      {items.map((item) => (
        <ImageCard
          key={item.id}
          item={item}
          ids={ids}
          backTo={backTo}
          selected={selected.has(item.id)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  );
}
