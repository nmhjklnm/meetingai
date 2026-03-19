import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#09090b",
        raised: "#111120",
        surface: "rgba(255,255,255,0.02)",
        "surface-hover": "rgba(255,255,255,0.03)",
        "surface-active": "rgba(255,255,255,0.04)",
        "text-primary": "rgba(255,255,250,0.85)",
        "text-secondary": "rgba(255,255,250,0.5)",
        "text-muted": "rgba(255,255,250,0.25)",
        "border-subtle": "rgba(255,255,255,0.05)",
        "border-focus": "rgba(255,255,250,0.15)",
        cream: "rgba(255,255,250,0.9)",
        "cream-hover": "rgba(255,255,250,1)",
        error: "rgba(255,120,120,0.6)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "PingFang SC", "sans-serif"],
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
