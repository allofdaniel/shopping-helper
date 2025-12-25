import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        daiso: '#FF6B35',
        costco: '#E31837',
        traders: '#004D9B',
        ikea: '#0051BA',
        oliveyoung: '#009A3D',
        coupang: '#E4002B',
        convenience: '#FFA500',
      },
    },
  },
  plugins: [],
}
export default config
