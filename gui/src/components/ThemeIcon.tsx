import { Feather, Wand2, Sparkles, Zap, Flame, Star, Heart, Gem, Crown, Rocket, LucideProps } from 'lucide-react'
import { BRAND_ICON, ThemeIconName } from '../config/themes'

// Map icon names to actual Lucide components
const ICON_MAP: Record<ThemeIconName, React.ComponentType<LucideProps>> = {
  feather: Feather,
  wand: Wand2,
  sparkles: Sparkles,
  zap: Zap,
  flame: Flame,
  star: Star,
  heart: Heart,
  gem: Gem,
  crown: Crown,
  rocket: Rocket,
}

interface ThemeIconProps extends LucideProps {
  /** Override the brand icon with a specific icon name */
  override?: ThemeIconName
}

/**
 * Renders the brand icon configured in themes.ts.
 *
 * Usage:
 *   <ThemeIcon className="w-8 h-8" />
 *
 * The icon is consistent across all themes.
 * To change the icon everywhere, update BRAND_ICON in themes.ts.
 */
export default function ThemeIcon({ override, ...props }: ThemeIconProps) {
  const iconName = override || BRAND_ICON
  const IconComponent = ICON_MAP[iconName]

  return <IconComponent {...props} />
}

/**
 * Get the brand icon component
 */
export function getBrandIcon(): React.ComponentType<LucideProps> {
  return ICON_MAP[BRAND_ICON]
}
