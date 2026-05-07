/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        /* Beige — primary surface / background tones */
        beige: {
          50:  "#fdf8f1",
          100: "#f8edd8",
          200: "#f0d9b0",
          300: "#e4c288",
          400: "#d4a55c",
        },
        /* Saffron — call-to-action / accent */
        saffron: {
          50:  "#fff8ed",
          100: "#ffeacc",
          200: "#ffd18a",
          300: "#ffb347",
          400: "#f59519",
          500: "#e07b0a",
          600: "#c46205",
          700: "#9e4a08",
        },
        /* Semantic aliases kept for backward-compat with existing Tailwind classes */
        border:  "#e2d5bf",
        ink:     "#3b2a14",
        muted:   "#8a6f4e",
        panel:   "#fdf8f1",
        brand:   "#c46205",   /* saffron-600 — primary action */
        amber:   "#9e4a08",   /* saffron-700 — dark accent */
        danger:  "#b42318",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 4px 0 rgba(59,42,20,0.08), 0 0 0 1px rgba(59,42,20,0.06)",
        "card-active": "0 0 0 2px #c46205, 0 2px 8px 0 rgba(196,98,5,0.18)",
      },
    },
  },
  plugins: [],
};
