/** Tailwind */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        lab: {
          bg: '#0b0714',
          panel: '#151021',
          line: '#2a2140',
          accent: '#a78bfa',
          green: '#34d399',
          amber: '#fbbf24',
          red: '#f87171',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
