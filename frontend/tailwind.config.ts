import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mahi: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          900: "#1e1b4b",
        },
        surface: {
          900: "#0f0f14",
          800: "#16161f",
          700: "#1e1e2a",
          600: "#26263a",
          500: "#30304a",
        },
      },
      keyframes: {
        blink: {
          "0%, 90%, 100%": { transform: "scaleY(1)" },
          "95%": { transform: "scaleY(0.1)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        orbit: {
          "0%": { transform: "rotate(0deg) translateX(18px) rotate(0deg)" },
          "100%": { transform: "rotate(360deg) translateX(18px) rotate(-360deg)" },
        },
        fadeUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        blink:  "blink 4s ease-in-out infinite",
        float:  "float 3s ease-in-out infinite",
        orbit:  "orbit 1.2s linear infinite",
        fadeUp: "fadeUp 0.25s ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
