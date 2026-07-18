/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand palette — adjust to institution branding.
        primary: {
          50: "#eef4ff", 100: "#d9e6ff", 200: "#b3ccff", 300: "#82a9ff",
          400: "#557fff", 500: "#3357f5", 600: "#2540d1", 700: "#1e33a8",
          800: "#1c2c85", 900: "#1b296a",
        },
        surface: {
          light: "#ffffff",
          dark: "#0f1420",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
