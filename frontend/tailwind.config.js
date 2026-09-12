/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        leaf: {
          50: '#f0faf3',
          100: '#dcf2e3',
          500: '#2e9e5b',
          600: '#227a46',
          700: '#1b6037',
          800: '#154c2b',
        },
      },
    },
  },
  plugins: [],
}