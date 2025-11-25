/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          green: '#00ff41',
          'green-dim': '#00cc34',
          cyan: '#00d4ff',
        },
      },
    },
  },
  plugins: [],
}
