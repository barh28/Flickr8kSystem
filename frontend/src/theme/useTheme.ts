import { useState } from "react";

import { applyTheme, getInitialTheme } from "./theme";
import type { Theme } from "./theme";

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
  }

  return { theme, toggle };
}
