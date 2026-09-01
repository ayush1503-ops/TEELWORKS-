/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#FAFAFA",
        fg: "#0F172A",
        muted: "#F1F5F9",
        mutext: "#64748B",
        electric: "#0052FF",
        electric2: "#4D7CFF",
        card: "#FFFFFF",
        dark: "#0F172A",
      },
      fontFamily: {
        display: ["Calistoga", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        soft: "0 8px 30px rgba(15, 23, 42, 0.06)",
        lift: "0 16px 50px rgba(15, 23, 42, 0.10)",
        glow: "0 0 40px rgba(0, 82, 255, 0.25)",
      },
    },
  },
  plugins: [],
};
