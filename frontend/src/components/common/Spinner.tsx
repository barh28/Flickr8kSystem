import styles from "./css/Spinner.module.css";

export default function Spinner() {
  return <span className={styles.spinner} role="status" aria-label="Loading" />;
}
