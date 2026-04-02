import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["Nunito", "sans-serif"],
        display: ["Lora", "serif"],
      },
      colors: {
        brand:  { DEFAULT: "#7c6af5", light: "#c4b5fd", dark: "#5b48e0" },
        muted:  "#7b7094",
        "chat-bg": "#faf8f5",
        sidebar: "#f3f0fa",
      },
      borderRadius: { msg: "18px" },
      boxShadow: {
        msg:  "0 2px 12px rgba(44,38,64,0.07)",
        card: "0 4px 24px rgba(44,38,64,0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
