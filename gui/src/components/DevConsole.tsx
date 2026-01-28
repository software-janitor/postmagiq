import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import { useDevStore, DEV_MODE_ENABLED, LLMMessage } from '../stores/devStore'

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return ts
  }
}

function ContextWarning({ warning }: { warning?: string }) {
  if (!warning) return null

  const isCritical = warning.toLowerCase().includes('critical')

  return (
    <div
      className={clsx(
        'px-2 py-1 rounded text-xs font-mono',
        isCritical ? 'bg-red-900/50 text-red-300' : 'bg-amber-900/50 text-amber-300'
      )}
    >
      {warning}
    </div>
  )
}

function MessageCard({ message }: { message: LLMMessage }) {
  const isRequest = message.type === 'request'

  return (
    <div
      className={clsx(
        'border rounded-lg p-3 mb-3',
        isRequest
          ? 'border-blue-800 bg-blue-950/30'
          : message.success
          ? 'border-green-800 bg-green-950/30'
          : 'border-red-800 bg-red-950/30'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'px-2 py-0.5 rounded text-xs font-semibold uppercase',
              isRequest ? 'bg-blue-800 text-blue-200' : 'bg-green-800 text-green-200'
            )}
          >
            {isRequest ? 'Request' : 'Response'}
          </span>
          <span className="text-zinc-400 text-sm">{message.state}</span>
          <span className="text-zinc-500 text-xs">({message.agent})</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span>{message.model}</span>
          <span>{formatTimestamp(message.timestamp)}</span>
        </div>
      </div>

      {/* Context Warning */}
      <ContextWarning warning={message.contextWarning} />

      {/* Request content */}
      {isRequest && (
        <div className="space-y-3 mt-2">
          {message.systemPrompt && (
            <div>
              <div className="text-xs text-purple-400 font-semibold mb-1">System Prompt:</div>
              <pre className="bg-zinc-900 p-2 rounded text-xs text-zinc-300 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {message.systemPrompt}
              </pre>
            </div>
          )}
          {message.userMessage && (
            <div>
              <div className="text-xs text-cyan-400 font-semibold mb-1">User Message:</div>
              <pre className="bg-zinc-900 p-2 rounded text-xs text-zinc-300 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {message.userMessage}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Response content */}
      {!isRequest && (
        <div className="space-y-3 mt-2">
          {message.error ? (
            <div>
              <div className="text-xs text-red-400 font-semibold mb-1">Error:</div>
              <pre className="bg-red-950 p-2 rounded text-xs text-red-300 overflow-x-auto">
                {message.error}
              </pre>
            </div>
          ) : (
            <div>
              <div className="text-xs text-green-400 font-semibold mb-1">Response:</div>
              <pre className="bg-zinc-900 p-2 rounded text-xs text-zinc-300 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap">
                {message.content}
              </pre>
            </div>
          )}

          {/* Token stats */}
          {message.tokens && (
            <div className="flex items-center gap-4 text-xs text-zinc-500">
              <span>
                Tokens: {message.tokens.input.toLocaleString()} in / {message.tokens.output.toLocaleString()} out
              </span>
              {message.durationMs && <span>Duration: {(message.durationMs / 1000).toFixed(2)}s</span>}
              {message.contextUsagePercent !== undefined && (
                <span
                  className={clsx(
                    message.contextUsagePercent > 80 ? 'text-amber-400' : '',
                    message.contextUsagePercent > 90 ? 'text-red-400' : ''
                  )}
                >
                  Context: {message.contextUsagePercent.toFixed(1)}%
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function DevConsole() {
  const { enabled, isOpen, messages, toggleOpen, clearMessages } = useDevStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages.length, isOpen])

  // Don't render if dev mode is not enabled
  if (!enabled && !DEV_MODE_ENABLED) {
    return null
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50">
      {/* Toggle bar */}
      <div
        className={clsx(
          'flex items-center justify-between px-4 py-2 cursor-pointer',
          'bg-zinc-900 border-t border-zinc-700',
          'hover:bg-zinc-800 transition-colors'
        )}
        onClick={toggleOpen}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-900 text-purple-300">
            DEV
          </span>
          <span className="text-sm text-zinc-400">
            LLM Console ({messages.length} messages)
          </span>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                clearMessages()
              }}
              className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1"
            >
              Clear
            </button>
          )}
          <span className="text-zinc-500">{isOpen ? '▼' : '▲'}</span>
        </div>
      </div>

      {/* Console content */}
      {isOpen && (
        <div className="bg-zinc-950 border-t border-zinc-800 h-96 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="text-center text-zinc-600 py-8">
              No LLM messages yet. Start a workflow to see requests and responses.
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageCard key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      )}
    </div>
  )
}
