const withMT = require("@material-tailwind/react/utils/withMT");
const colors = require("tailwindcss/colors");

module.exports = withMT({
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      keyframes: {
        "bounce-subtle": {
          "0%, 100%": { transform: "translateY(0) scale(1.1)" },
          "50%": { transform: "translateY(-3px) scale(1.1)" },
        },
      },
      animation: {
        "bounce-subtle": "bounce-subtle 1.5s ease-in-out infinite",
      },
      colors: {
        gray: colors.gray,
        blue: {
          ...colors.blue,
          DEFAULT: "#3066FF",
          500: "#3066FF",
        },
        yellow: {
          DEFAULT: "#F19937",
          500: "#F19937",
        },
        red: {
          ...colors.red,
          DEFAULT: "#EA4E3D",
          500: "#EA4E3D",
        },
        green: {
          DEFAULT: "#67C23A",
          500: "#67C23A",
        },
        sky: {
          DEFAULT: "#55A6F8",
          500: "#55A6F8",
        },
        slate: {
          DEFAULT: "#64748B",
          500: "#64748B",
        },
        dark: {
          DEFAULT: "#1E293B",
          500: "#0F172A",
        },
      },
    },
  },
  plugins: [],
});
