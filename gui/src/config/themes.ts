/**
 * Theme Configuration
 *
 * To add a new theme:
 * 1. Add a new entry to the THEMES object below
 * 2. That's it! The theme will automatically appear in the theme switcher.
 *
 * Theme structure:
 * - name: Display name in the theme switcher
 * - primary: Main accent color (e.g., 'violet', 'emerald')
 * - secondary: Secondary accent color for gradients
 * - Each color maps to Tailwind color classes
 *
 * Brand icon: Change BRAND_ICON below to update the icon everywhere
 * Available icons: feather, wand, sparkles, zap, flame, star, heart, gem, crown, rocket
 */

export type ThemeIconName = 'feather' | 'wand' | 'sparkles' | 'zap' | 'flame' | 'star' | 'heart' | 'gem' | 'crown' | 'rocket'

// Single brand icon used across all themes - change this to update everywhere
export const BRAND_ICON: ThemeIconName = 'wand'

export interface ThemeConfig {
  name: string
  primary: string
  secondary: string
}

// Add your themes here - just add a new entry to this object
export const THEMES: Record<string, ThemeConfig> = {
  violet: {
    name: 'Violet',
    primary: 'violet',
    secondary: 'fuchsia',
  },
  emerald: {
    name: 'Emerald',
    primary: 'emerald',
    secondary: 'teal',
  },
  cyan: {
    name: 'Cyan',
    primary: 'cyan',
    secondary: 'sky',
  },
  crimson: {
    name: 'Crimson',
    primary: 'red',
    secondary: 'orange',
  },
  amber: {
    name: 'Amber',
    primary: 'amber',
    secondary: 'yellow',
  },
  rose: {
    name: 'Rose',
    primary: 'rose',
    secondary: 'pink',
  },
}

export type ThemeId = keyof typeof THEMES

// Generate Tailwind classes from theme config
export function generateThemeClasses(config: ThemeConfig) {
  const { primary, secondary } = config

  return {
    // Gradients
    gradient: `from-${primary}-600 to-${secondary}-600`,
    gradientHover: `hover:from-${primary}-500 hover:to-${secondary}-500`,
    gradientDisabled: `disabled:from-${primary}-800 disabled:to-${secondary}-800`,
    gradientText: `from-${primary}-300 to-${secondary}-300`,

    // Backgrounds
    bgGlow1: `bg-${primary}-600/20`,
    bgGlow2: `bg-${secondary}-600/20`,
    bgActive: `bg-gradient-to-r from-${primary}-600 to-${secondary}-600`,
    bgHover: `hover:bg-${primary}-950/50`,
    bgMuted: `bg-${primary}-600/20`,

    // Borders
    border: `border-${primary}-500/50`,
    borderPrimary: `border-${primary}-500`,
    borderHover: `hover:border-${primary}-500/50`,

    // Text
    textPrimary: `text-${primary}-400`,
    textSecondary: `text-${secondary}-400`,
    textMuted: `text-${primary}-400/70`,

    // Shadows
    shadow: `shadow-${primary}-500/25`,

    // Icons
    iconPrimary: `text-${secondary}-400`,
    iconSecondary: `text-${primary}-400`,
  }
}

// Pre-generate all theme classes for Tailwind's JIT compiler to detect
// This ensures all dynamic classes are included in the build
export const ALL_THEME_CLASSES = Object.values(THEMES).flatMap(config => {
  const { primary, secondary } = config
  return [
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
  ]
})
