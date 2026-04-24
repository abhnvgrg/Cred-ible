import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#818cf8",
        secondary: "#a78bfa",
        tertiary: "#34d399",
        surface: "#030712",
        "surface-low": "#0b0f19",
        "surface-card": "#111827",
        "surface-raise": "#1f2937",
        "outline-variant": "#374151"
      }
    }
  },
  plugins: []
};

export default config;
