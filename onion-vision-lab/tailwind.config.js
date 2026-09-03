/** Onion Vision Lab — light design tokens (F1: white bg, ink #0F172A, electric #0052FF) */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#FFFFFF',
        fg: '#0F172A',
        ink: '#0F172A',
        mutext: '#5B6B83',
        faint: '#94A3B8',
        line: '#E5EAF3',
        card: '#FFFFFF',
        electric: '#0052FF',
        electric2: '#4D7CFF',
        electricSoft: '#EEF4FF',
        green: '#15803D',
        greenSoft: '#ECFDF5',
        amber: '#B45309',
        amberSoft: '#FFFBEB',
        red: '#B91C1C',
        redSoft: '#FEF2F2',
        lab: {
          green: '#16A34A',
          amber: '#D97706',
          red: '#DC2626',
        },
      },
      fontFamily: {
        display: ['ui-rounded', 'Arial Rounded MT Bold', 'Trebuchet MS', 'system-ui', 'sans-serif'],
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        soft: '0 8px 30px rgba(15, 23, 42, 0.07)',
        lift: '0 18px 50px rgba(15, 23, 42, 0.12)',
        glow: '0 0 36px rgba(0, 82, 255, 0.28)',
      },
      keyframes: {
        floaty: {
          '0%,100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-7px)' },
        },
      },
      animation: {
        floaty: 'floaty 5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
