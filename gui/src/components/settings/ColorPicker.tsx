import { useState, useEffect } from 'react'

interface ColorPickerProps {
  label: string
  value: string | null | undefined
  onChange: (color: string) => void
  description?: string
}

/**
 * Simple color picker with hex value display and preview swatch
 */
export default function ColorPicker({ label, value, onChange, description }: ColorPickerProps) {
  const [hexInput, setHexInput] = useState(value || '#000000')

  // Sync hex input when value prop changes
  useEffect(() => {
    if (value && value !== hexInput) {
      setHexInput(value)
    }
  }, [value])

  const handleColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newColor = e.target.value
    setHexInput(newColor)
    onChange(newColor)
  }

  const handleHexInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let input = e.target.value.toUpperCase()
    // Ensure it starts with #
    if (!input.startsWith('#')) {
      input = '#' + input
    }
    // Limit to 7 characters (#XXXXXX)
    input = input.slice(0, 7)
    setHexInput(input)

    // Only update parent if valid hex
    if (/^#[0-9A-F]{6}$/i.test(input)) {
      onChange(input)
    }
  }

  const displayColor = value || '#000000'

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-zinc-300">{label}</label>
      {description && <p className="text-xs text-zinc-500">{description}</p>}
      <div className="flex items-center gap-3">
        {/* Color swatch / native picker */}
        <div className="relative">
          <div
            className="w-10 h-10 rounded-lg border border-zinc-600 cursor-pointer"
            style={{ backgroundColor: displayColor }}
          />
          <input
            type="color"
            value={displayColor}
            onChange={handleColorChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>

        {/* Hex input */}
        <input
          type="text"
          value={hexInput}
          onChange={handleHexInputChange}
          placeholder="#000000"
          maxLength={7}
          className="w-28 px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white font-mono text-sm uppercase focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500"
        />
      </div>
    </div>
  )
}
