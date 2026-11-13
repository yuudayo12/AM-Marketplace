/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#08090c", 900: "#0d0e12", 850: "#111318", 800: "#15171d", 750: "#1a1d24", 700: "#23262f", 600: "#2e323d", 500: "#454a57" },
        violet: { 300: "#c4b5fd", 400: "#a78bfa", 500: "#8b5cf6", 600: "#7c3aed" },
        azure: { 300: "#93c5fd", 400: "#60a5fa", 500: "#3b82f6" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(139,92,246,.35), 0 10px 40px -10px rgba(139,92,246,.55)",
        panel: "0 1px 0 0 rgba(255,255,255,.03) inset, 0 20px 50px -25px rgba(0,0,0,.8)",
      },
      keyframes: {
        "fade-up": { "0%": { opacity: 0, transform: "translateY(8px)" }, "100%": { opacity: 1, transform: "none" } },
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        "bar-pulse": { "0%,100%": { transform: "scaleY(.35)" }, "50%": { transform: "scaleY(1)" } },
      },
      animation: {
        "fade-up": "fade-up .45s cubic-bezier(.2,.7,.2,1) both",
        shimmer: "shimmer 1.6s linear infinite",
        "bar-pulse": "bar-pulse 1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
