import { useSyncExternalStore } from "react";

import { dismissToast, getToasts, subscribe } from "./toastStore";
import type { ToastType } from "./toastStore";
import styles from "./css/Toaster.module.css";

const TYPE_CLASS: Record<ToastType, string> = {
  error: styles.error,
  success: styles.success,
  info: styles.info,
};

export default function Toaster() {
  const toasts = useSyncExternalStore(subscribe, getToasts);

  if (toasts.length === 0) return null;

  return (
    <div className={styles.container} role="region" aria-label="Notifications">
      {toasts.map((item) => (
        <div key={item.id} className={`${styles.toast} ${TYPE_CLASS[item.type]}`} role="alert">
          <span className={styles.message}>{item.message}</span>
          <button
            type="button"
            className={styles.close}
            onClick={() => dismissToast(item.id)}
            aria-label="Dismiss notification"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
