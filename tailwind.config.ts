import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        orange: {
          DEFAULT: "#FF5500",
          light: "#FF7A33",
          dark: "rgba(255,85,0,0.15)",
          glow: "rgba(255,85,0,0.08)",
          500: "#FF5500",
          600: "#E84F00",
        },
        bg: {
          DEFAULT: "#0a0a0a",
          2: "#111111",
          3: "#181818",
          card: "#1e1e1e",
          card2: "#242424",
        },
        text: {
          DEFAULT: "#F0ECE6",
          secondary: "#A09890",
          muted: "#5E5850",
        },
        border: {
          DEFAULT: "rgba(255,255,255,0.07)",
          strong: "rgba(255,255,255,0.12)",
        },
      },
      fontFamily: {
        display: ["Bebas Neue", "sans-serif"],
        heading: ["Barlow Condensed", "sans-serif"],
        body: ["DM Sans", "sans-serif"],
        mono: ["DM Mono", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "orange-glow": "radial-gradient(ellipse at top, rgba(255,85,0,0.15) 0%, transparent 60%)",
      },
      boxShadow: {
        "orange": "0 0 30px rgba(255,85,0,0.3)",
        "orange-sm": "0 0 12px rgba(255,85,0,0.2)",
        "card": "0 4px 24px rgba(0,0,0,0.4)",
      },
      animation: {
        "pulse-orange": "pulse-orange 2s ease-in-out infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
      },
      keyframes: {
        "pulse-orange": {
          "0%, 100%": { boxShadow: "0 0 12px rgba(255,85,0,0.2)" },
          "50%": { boxShadow: "0 0 24px rgba(255,85,0,0.5)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
