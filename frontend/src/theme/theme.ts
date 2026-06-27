// Theme persistence + application. Light is the default; dark applies the
// alternate palette via the `data-theme` attribute on <html>.
export type Theme = "light" | "dark";

const STORAGE_KEY = "flickr8k.theme";

export function getInitialTheme(): Theme {
  return localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(STORAGE_KEY, theme);
}
