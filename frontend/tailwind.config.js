/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Two-tone rhythm: near-black bands and warm off-white bands
        ink: {
          DEFAULT: "#0a0a0a",
          900: "#111111",
          800: "#1a1a1a",
          700: "#262626",
          600: "#3a3a3a",
        },
        paper: {
          DEFAULT: "#f5f4f0",
          card: "#ecebe5",
          line: "#e2e0d8",
        },
        muted: {
          dark: "#8a8a8a",  // body copy on ink
          light: "#555555", // body copy on paper
        },
        // The only accent; reserved for primary calls to action
        accent: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
        },
        // Semantic, used sparingly for verification verdicts only
        ok: "#16a34a",
        bad: "#dc2626",
        warn: "#ca8a04",
      },
      fontFamily: {
        sans: ["Geist", "system-ui", "-apple-system", "sans-serif"],
        mono: ["'Geist Mono'", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        display: "-0.035em",
      },
      borderRadius: {
        card: "20px",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        marquee: {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-50%)" },
        },
      },
      animation: {
        float: "float 7s ease-in-out infinite",
        "float-slow": "float 9s ease-in-out infinite",
        "fade-up": "fade-up 0.7s cubic-bezier(0.2, 0.7, 0.2, 1) both",
        "fade-in": "fade-in 0.25s ease-out both",
      },
    },
  },
  plugins: [],
}
