"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { setTheme, theme } = useTheme();

  return (
    <button
      onClick={() => setTheme(theme === "light" ? "dark" : "light")}
      className="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-full transition-colors hover:bg-white/10 dark:hover:bg-slate-800"
      aria-label="Toggle theme"
    >
      <Sun className="h-[1.1rem] w-[1.1rem] text-slate-600 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-[1.1rem] w-[1.1rem] rotate-90 scale-0 text-slate-400 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </button>
  );
}
