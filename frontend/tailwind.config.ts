import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: "hsl(var(--primary))",
        secondary: "hsl(var(--secondary))",
        tertiary: "hsl(var(--tertiary))",
        surface: "hsl(var(--surface))",
        "surface-low": "hsl(var(--surface-low))",
        "surface-card": "hsl(var(--surface-card))",
        "surface-raise": "hsl(var(--surface-raise))",
        "outline-variant": "hsl(var(--outline-variant))",
        slate: {
          50: "hsl(var(--slate-50))",
          100: "hsl(var(--slate-100))",
          200: "hsl(var(--slate-200))",
          300: "hsl(var(--slate-300))",
          400: "hsl(var(--slate-400))",
          500: "hsl(var(--slate-500))",
          600: "hsl(var(--slate-600))",
          700: "hsl(var(--slate-700))",
          800: "hsl(var(--slate-800))",
          900: "hsl(var(--slate-900))",
          950: "hsl(var(--slate-950))",
        },
        indigo: {
          50: "hsl(var(--indigo-50))",
          100: "hsl(var(--indigo-100))",
          200: "hsl(var(--indigo-200))",
          300: "hsl(var(--indigo-300))",
          400: "hsl(var(--indigo-400))",
          500: "hsl(var(--indigo-500))",
          600: "hsl(var(--indigo-600))",
          700: "hsl(var(--indigo-700))",
          800: "hsl(var(--indigo-800))",
          900: "hsl(var(--indigo-900))",
          950: "hsl(var(--indigo-950))",
        },
        white: "hsl(var(--white))",
        black: "hsl(var(--black))",
      }
    }
  },
  plugins: []
};

export default config;
