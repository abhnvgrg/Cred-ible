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
        primary: "#a3a6ff",
        secondary: "#c180ff",
        tertiary: "#6bff8f",
        surface: "#0a0e19",
        "surface-low": "#0f131f",
        "surface-card": "#141927",
        "surface-raise": "#202535",
        "outline-variant": "#444855"
      }
    }
  },
  plugins: []
};

export default config;
