import type { Config } from "tailwindcss";

// ChogHub "Sticker Riot" tokens: sunshine paper, ink outlines, hard shadows.
// Purple is the brand, mint means done, pink is for prizes and badges.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sun: "#FFE14D",
        "sun-dot": "#F2C928",
        ink: "#1B0B3A",
        "ink-soft": "#4A3D6B",
        grape: "#6C3BFF",
        "grape-light": "#8F6BFF",
        bubble: "#FF7AC6",
        "bubble-light": "#FF93D2",
        hot: "#FF4F9A",
        mint: "#3DDC97",
        alarm: "#B3123F",
      },
      fontFamily: {
        display: ["'Lilita One'", "system-ui", "sans-serif"],
        body: ["Outfit", "system-ui", "sans-serif"],
      },
      borderWidth: { 3: "3px" },
      boxShadow: {
        hard: "4px 4px 0 0 #1B0B3A",
        "hard-md": "6px 6px 0 0 #1B0B3A",
        "hard-lg": "10px 10px 0 0 #1B0B3A",
      },
    },
  },
  plugins: [],
};

export default config;
