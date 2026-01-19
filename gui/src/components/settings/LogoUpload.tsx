import { useCallback, useState } from 'react'
import { Upload, X, Image as ImageIcon } from 'lucide-react'
import { clsx } from 'clsx'

interface LogoUploadProps {
  label: string
  currentUrl: string | null
  onUpload: (file: File) => Promise<void>
  onRemove: () => Promise<void>
  description?: string
  accept?: string
  maxSizeMB?: number
  isUploading?: boolean
}

/**
 * Drag-and-drop file upload with preview and remove button
 */
export default function LogoUpload({
  label,
  currentUrl,
  onUpload,
  onRemove,
  description,
  accept = 'image/png,image/jpeg,image/svg+xml',
  maxSizeMB = 2,
  isUploading = false,
}: LogoUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validateFile = (file: File): string | null => {
    // Check file type
    const validTypes = accept.split(',').map((t) => t.trim())
    if (!validTypes.includes(file.type)) {
      return `Invalid file type. Accepted: ${validTypes.map((t) => t.split('/')[1]).join(', ')}`
    }

    // Check file size
    const maxBytes = maxSizeMB * 1024 * 1024
    if (file.size > maxBytes) {
      return `File too large. Maximum size: ${maxSizeMB}MB`
    }

    return null
  }

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      const validationError = validateFile(file)
      if (validationError) {
        setError(validationError)
        return
      }

      try {
        await onUpload(file)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      }
    },
    [onUpload, accept, maxSizeMB]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)

      const file = e.dataTransfer.files[0]
      if (file) {
        handleFile(file)
      }
    },
    [handleFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        handleFile(file)
      }
      // Reset input so same file can be selected again
      e.target.value = ''
    },
    [handleFile]
  )

  const handleRemove = async () => {
    setError(null)
    try {
      await onRemove()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Remove failed')
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-zinc-300">{label}</label>
      {description && <p className="text-xs text-zinc-500">{description}</p>}

      {currentUrl ? (
        // Preview mode
        <div className="relative inline-block">
          <div className="p-4 bg-zinc-800 rounded-lg border border-zinc-600">
            <img
              src={currentUrl}
              alt={label}
              className="max-h-24 max-w-48 object-contain"
            />
          </div>
          <button
            onClick={handleRemove}
            disabled={isUploading}
            className="absolute -top-2 -right-2 w-6 h-6 bg-red-600 hover:bg-red-700 text-white rounded-full flex items-center justify-center transition-colors disabled:opacity-50"
            title="Remove"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        // Upload mode
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={clsx(
            'relative border-2 border-dashed rounded-lg p-6 transition-colors cursor-pointer',
            isDragging
              ? 'border-amber-500 bg-amber-500/10'
              : 'border-zinc-600 hover:border-zinc-500 bg-zinc-800/50'
          )}
        >
          <input
            type="file"
            accept={accept}
            onChange={handleInputChange}
            disabled={isUploading}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          />
          <div className="flex flex-col items-center gap-2 text-center">
            {isUploading ? (
              <>
                <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-zinc-400">Uploading...</span>
              </>
            ) : (
              <>
                <div className="w-12 h-12 bg-zinc-700 rounded-full flex items-center justify-center">
                  {isDragging ? (
                    <ImageIcon className="w-6 h-6 text-amber-400" />
                  ) : (
                    <Upload className="w-6 h-6 text-zinc-400" />
                  )}
                </div>
                <div>
                  <p className="text-sm text-zinc-300">
                    {isDragging ? 'Drop file here' : 'Drag and drop or click to upload'}
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">
                    PNG, JPG, or SVG up to {maxSizeMB}MB
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-400 mt-1">{error}</p>
      )}
    </div>
  )
}
