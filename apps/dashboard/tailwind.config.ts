import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202A",
        line: "#D9E2EC",
        surface: "#F7F9FB",
        signal: "#0F766E",
        risk: "#B91C1C",
        wait: "#A16207",
        action: "#1D4ED8"
      }
    }
  },
  plugins: []
} satisfies Config;

