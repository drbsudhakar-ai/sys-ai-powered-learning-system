/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",       // include App Router if you use Next.js 13+
    "./pages/**/*.{js,ts,jsx,tsx}",     // Page Router
    "./components/**/*.{js,ts,jsx,tsx}",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./styles/**/*.{css}"               // include your CSS files
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#f97316",
          dark: "#ea580c"
        }
      },
      animation: {
        'fade-in': 'fadeIn 1s ease-in-out',
        'bounce-slow': 'bounce 3s infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        pulseGlow: {
          '0%, 100%': {
            boxShadow: '0 0 20px rgba(99,102,241,0.6), 0 0 40px rgba(236,72,153,0.4)',
          },
          '50%': {
            boxShadow: '0 0 40px rgba(99,102,241,0.9), 0 0 80px rgba(236,72,153,0.7)',
          },
        },


      },

      fontFamily: {
        sans: ["Inter", "sans-serif"]
      }
    }
  },
  darkMode: "class",
  plugins: []
};
