import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "var(--color-base)",
        raised: "var(--color-raised)",
        surface: {
          DEFAULT: "rgb(var(--neutral) / 0.02)",
          hover: "rgb(var(--neutral) / 0.03)",
          active: "rgb(var(--neutral) / 0.04)",
        },
        "text-primary": "rgb(var(--fg) / 0.85)",
        "text-secondary": "rgb(var(--fg) / 0.5)",
        "text-muted": "rgb(var(--fg) / 0.25)",
        "border-subtle": "rgb(var(--neutral) / 0.05)",
        "border-focus": "rgb(var(--fg) / 0.15)",
        cream: {
          DEFAULT: "rgb(var(--fg) / 0.9)",
          hover: "rgb(var(--fg) / 1)",
        },
        error: "var(--color-error)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "PingFang SC",
          "sans-serif",
        ],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
      },
    },
  },
  plugins: [],
} satisfies Config;
