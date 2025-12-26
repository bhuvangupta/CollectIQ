/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        // Modern AI-inspired teal/cyan primary
        primary: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        // Accent color - emerald for success
        accent: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        // AI/Voice color - violet/purple
        ai: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
          950: '#2e1065',
        },
        // Light theme grays (slate scale)
        light: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'ai-gradient': 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #f8fafc 100%)',
        'card-gradient': 'linear-gradient(145deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)',
        'glow-gradient': 'radial-gradient(ellipse at center, rgba(6,182,212,0.08) 0%, transparent 70%)',
        'mesh-gradient': 'radial-gradient(at 40% 20%, rgba(139, 92, 246, 0.08) 0px, transparent 50%), radial-gradient(at 80% 0%, rgba(6, 182, 212, 0.08) 0px, transparent 50%), radial-gradient(at 0% 50%, rgba(16, 185, 129, 0.08) 0px, transparent 50%)',
        'ai-mesh': 'radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 40%), radial-gradient(at 0% 100%, rgba(6, 182, 212, 0.12) 0px, transparent 40%)',
        'grid-pattern': 'linear-gradient(rgba(6, 182, 212, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 0.03) 1px, transparent 1px)',
        'shine': 'linear-gradient(110deg, transparent 25%, rgba(255,255,255,0.3) 50%, transparent 75%)',
      },
      backgroundSize: {
        'grid': '32px 32px',
        'shine': '200% 100%',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(6, 182, 212, 0.25)',
        'glow-lg': '0 0 40px rgba(6, 182, 212, 0.3)',
        'glow-ai': '0 0 30px rgba(139, 92, 246, 0.3)',
        'glow-accent': '0 0 20px rgba(16, 185, 129, 0.25)',
        'inner-glow': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.8)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)',
        'card-hover': '0 20px 40px -12px rgba(0, 0, 0, 0.12), 0 8px 20px -8px rgba(0, 0, 0, 0.08)',
        'card-glow': '0 0 0 1px rgba(6, 182, 212, 0.1), 0 4px 20px rgba(6, 182, 212, 0.12)',
        'soft': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'float': '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.08)',
        'inner-light': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.5)',
        'btn': '0 1px 2px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1)',
        'btn-hover': '0 4px 12px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'spin-slow': 'spin 8s linear infinite',
        'breathe': 'breathe 4s ease-in-out infinite',
        'wave': 'wave 1.5s ease-in-out infinite',
        'ripple': 'ripple 1.5s ease-out infinite',
        'fade-in': 'fade-in 0.4s ease-out forwards',
        'fade-in-up': 'fade-in-up 0.4s ease-out forwards',
        'fade-in-down': 'fade-in-down 0.4s ease-out forwards',
        'fade-in-scale': 'fade-in-scale 0.3s ease-out forwards',
        'slide-in-right': 'slide-in-right 0.3s ease-out forwards',
        'slide-in-left': 'slide-in-left 0.3s ease-out forwards',
        'slide-in-up': 'slide-in-up 0.3s ease-out forwards',
        'count-up': 'count-up 0.5s ease-out forwards',
        'draw': 'draw 1s ease-out forwards',
        'orbit': 'orbit 12s linear infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'bounce-subtle': 'bounce-subtle 2s ease-in-out infinite',
        'scale-in': 'scale-in 0.2s ease-out forwards',
        'shake': 'shake 0.5s ease-in-out',
        'gradient-x': 'gradient-x 3s ease infinite',
        'shine': 'shine 1.5s ease-in-out infinite',
        'pulse-ring': 'pulse-ring 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up-fade': 'slide-up-fade 0.3s ease-out forwards',
        'number-scroll': 'number-scroll 0.5s ease-out forwards',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(6, 182, 212, 0.15)' },
          '100%': { boxShadow: '0 0 20px rgba(6, 182, 212, 0.25)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 10px rgba(139, 92, 246, 0.3), 0 0 20px rgba(139, 92, 246, 0.2)' },
          '50%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.5), 0 0 40px rgba(139, 92, 246, 0.3)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.8' },
          '50%': { transform: 'scale(1.05)', opacity: '1' },
        },
        wave: {
          '0%, 100%': { transform: 'scaleY(0.5)' },
          '50%': { transform: 'scaleY(1)' },
        },
        ripple: {
          '0%': { transform: 'scale(1)', opacity: '0.4' },
          '100%': { transform: 'scale(2)', opacity: '0' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in-down': {
          '0%': { opacity: '0', transform: 'translateY(-16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in-scale': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'slide-in-left': {
          '0%': { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'slide-in-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'count-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        draw: {
          '0%': { strokeDashoffset: '100' },
          '100%': { strokeDashoffset: '0' },
        },
        orbit: {
          '0%': { transform: 'rotate(0deg) translateX(8px) rotate(0deg)' },
          '100%': { transform: 'rotate(360deg) translateX(8px) rotate(-360deg)' },
        },
        'bounce-subtle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
        'gradient-x': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        shine: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(2)', opacity: '0' },
        },
        'slide-up-fade': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'number-scroll': {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      transitionTimingFunction: {
        'bounce-in': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        'snappy': 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
        '400': '400ms',
      },
      scale: {
        '102': '1.02',
        '103': '1.03',
      },
    },
  },
  plugins: [],
}
