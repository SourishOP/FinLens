/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        hsbc: {
          red: "#DB0011",
          dark: "#111827",
          slate: "#1c2230",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)",
        cardhover: "0 8px 24px rgba(0,0,0,0.10)",
      },
    },
  },
  plugins: [],
};
