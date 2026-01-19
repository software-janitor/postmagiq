/** @type {import('tailwindcss').Config} */

// All theme color combinations that need to be safelisted
const themeColors = [
  { primary: 'violet', secondary: 'fuchsia' },
  { primary: 'emerald', secondary: 'teal' },
  { primary: 'cyan', secondary: 'sky' },
  { primary: 'red', secondary: 'orange' },
  { primary: 'amber', secondary: 'yellow' },
  { primary: 'rose', secondary: 'pink' },
]

// Generate all theme classes for safelist
const themeSafelist = themeColors.flatMap(({ primary, secondary }) => [
  // Gradients
  `from-${primary}-600`, `to-${secondary}-600`,
  `from-${primary}-500`, `to-${secondary}-500`,
  `from-${primary}-800`, `to-${secondary}-800`,
  `from-${primary}-300`, `to-${secondary}-300`,
  `hover:from-${primary}-500`, `hover:to-${secondary}-500`,
  `disabled:from-${primary}-800`, `disabled:to-${secondary}-800`,
  // Backgrounds
  `bg-${primary}-600/20`, `bg-${secondary}-600/20`,
  `bg-${primary}-950/50`, `hover:bg-${primary}-950/50`,
  // Borders
  `border-${primary}-500/50`, `border-${primary}-500`, `border-${primary}-900/50`,
  `hover:border-${primary}-500/50`,
  // Text
  `text-${primary}-400`, `text-${secondary}-400`,
  `text-${primary}-400/70`,
  // Shadows
  `shadow-${primary}-500/25`,
])

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: themeSafelist,
  theme: {
    extend: {
      colors: {
        // State type colors
        'state-initial': '#6366f1',
        'state-fanout': '#8b5cf6',
        'state-single': '#3b82f6',
        'state-orchestrator': '#f59e0b',
        'state-approval': '#10b981',
        'state-terminal': '#ef4444',
        'state-complete': '#22c55e',
      },
    },
  },
  plugins: [],
}
