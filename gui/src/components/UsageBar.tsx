import { clsx } from 'clsx'

interface UsageBarProps {
  label: string
  used: number
  limit: number
  unit?: string
  unlimited?: boolean
  showPercentage?: boolean
}

export default function UsageBar({
  label,
  used,
  limit,
  unit = '',
  unlimited = false,
  showPercentage = true,
}: UsageBarProps) {
  const percentage = unlimited || limit === 0 ? 0 : Math.min((used / limit) * 100, 100)
  const isOverLimit = !unlimited && limit > 0 && used > limit
  const isNearLimit = !unlimited && limit > 0 && percentage >= 80

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-zinc-400">{label}</span>
        <span className="text-white">
          {used.toLocaleString()}
          {!unlimited && limit > 0 && (
            <>
              {' / '}
              {limit.toLocaleString()}
            </>
          )}
          {unit && ` ${unit}`}
          {unlimited && ' (unlimited)'}
        </span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-300',
            isOverLimit
              ? 'bg-red-500'
              : isNearLimit
              ? 'bg-amber-500'
              : 'bg-green-500'
          )}
          style={{ width: unlimited ? '0%' : `${percentage}%` }}
        />
      </div>
      {showPercentage && !unlimited && limit > 0 && (
        <div className="text-xs text-zinc-500">
          {percentage.toFixed(0)}% used
          {isOverLimit && (
            <span className="text-red-400 ml-2">
              ({(used - limit).toLocaleString()} over limit)
            </span>
          )}
        </div>
      )}
    </div>
  )
}
