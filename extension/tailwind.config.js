/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        zen: {
          bg: "var(--zen-bg, #1a1a2e)",
          surface: "var(--zen-surface, #16213e)",
          primary: "var(--zen-primary, #0f3460)",
          accent: "var(--zen-accent, #e94560)",
          text: "var(--zen-text, #eaeaea)",
          muted: "var(--zen-muted, #8a8a9a)",
          border: "var(--zen-border, #2a2a4a)",
        },
      },
      fontFamily: {
        zen: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
