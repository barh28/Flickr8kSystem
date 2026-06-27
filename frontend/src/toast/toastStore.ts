// Tiny framework-agnostic toast store. It lives outside React so it can be
// triggered from anywhere (e.g. the React Query cache error handlers), and the
// <Toaster /> subscribes to it via useSyncExternalStore.
export type ToastType = "error" | "success" | "info";

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

type Listener = () => void;

let toasts: Toast[] = [];
const listeners = new Set<Listener>();
let nextId = 1;

const DEFAULT_DURATION = 5000;

function emit() {
  for (const listener of listeners) listener();
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getToasts(): Toast[] {
  return toasts;
}

export function dismissToast(id: number): void {
  toasts = toasts.filter((item) => item.id !== id);
  emit();
}

export function showToast(
  message: string,
  type: ToastType = "error",
  duration = DEFAULT_DURATION,
): number {
  const id = nextId++;
  toasts = [...toasts, { id, type, message }];
  emit();
  if (duration > 0) {
    setTimeout(() => dismissToast(id), duration);
  }
  return id;
}

export const toast = {
  error: (message: string) => showToast(message, "error"),
  success: (message: string) => showToast(message, "success"),
  info: (message: string) => showToast(message, "info"),
};
