import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#ffffff",
        foreground: "#171717",
        
        // CELO Brand Colors - Direct values for better compatibility
        'celo-yellow': '#FFC300',
        'celo-yellow-hover': '#E6B000',
        'celo-yellow-light': '#FFF3CC',
        'celo-gray': '#7F7F7F',
        'celo-gray-light': '#F5F5F5',
        'celo-gray-dark': '#4A4A4A',
        'celo-text-primary': '#000000',
        'celo-text-secondary': '#7F7F7F',
        'celo-text-light': '#B3B3B3',
        
        // Status Colors
        'success': '#10B981',
        'error': '#EF4444',
        'warning': '#F59E0B',
        'info': '#3B82F6',
        
        // Background Colors
        'bg-primary': '#FFFFFF',
        'bg-secondary': '#F9FAFB',
        'bg-tertiary': '#F3F4F6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config; 