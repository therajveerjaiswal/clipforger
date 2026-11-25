/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0E14",
        foreground: "#F0F3F6",
        surface: "#121721",
        surfaceBorder: "#1E2638",
        brand: {
          50: "#EEF2FF",
          100: "#E0E7FF",
          200: "#C7D2FE",
          300: "#A5B4FC",
          400: "#818CF8",
          500: "#6366F1",
          600: "#4F46E5",
          700: "#4338CA",
          800: "#3730A3",
          900: "#312E81",
          950: "#1E1B4B",
        },
        accent: {
          cyan: "#06B6D4",
          amber: "#F59E0B",
          emerald: "#10B981",
          rose: "#F43F5E",
        }
      },
      fontFamily: {
        sans: ["Inter", "Montserrat", "sans-serif"],
      },
    },
  },
  plugins: [],
};
