import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, AlertCircle, CheckCircle } from 'lucide-react'
import { apiGet, apiPut, apiPost } from '../api/client'
import StateMachineCanvas from '../components/workflow/StateMachineCanvas'

export default function Editor() {
  const queryClient = useQueryClient()
  const [yamlContent, setYamlContent] = useState('')
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    errors: string[]
    warnings: string[]
  } | null>(null)

  const { data: config, isLoading: _isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: () => apiGet<{ config: string }>('/config'),
  })

  // Sync config to state when data loads
  useEffect(() => {
    if (config?.config) {
      setYamlContent(config.config)
    }
  }, [config])

  const validateMutation = useMutation({
    mutationFn: (config: string) =>
      apiPost<{ valid: boolean; errors: string[]; warnings: string[] }>(
        '/config/validate',
        { config }
      ),
    onSuccess: (result) => setValidationResult(result),
  })

  const saveMutation = useMutation({
    mutationFn: (config: string) => apiPut('/config', { config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] })
      setValidationResult({ valid: true, errors: [], warnings: [] })
    },
  })

  const handleValidate = () => {
    validateMutation.mutate(yamlContent)
  }

  const handleSave = () => {
    saveMutation.mutate(yamlContent)
  }

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">State Machine Editor</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={handleValidate}
            className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600"
          >
            Validate
          </button>
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>
      </div>

      {/* Validation Messages */}
      {validationResult && (
        <div className={`p-4 rounded-lg ${
          validationResult.valid
            ? 'bg-green-500/10 border border-green-500/30'
            : 'bg-red-500/10 border border-red-500/30'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            {validationResult.valid ? (
              <>
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span className="text-green-400 font-medium">Configuration is valid</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-5 h-5 text-red-400" />
                <span className="text-red-400 font-medium">Validation errors</span>
              </>
            )}
          </div>
          {validationResult.errors.map((err, i) => (
            <div key={i} className="text-sm text-red-400 ml-7">{err}</div>
          ))}
          {validationResult.warnings.map((warn, i) => (
            <div key={i} className="text-sm text-yellow-400 ml-7">{warn}</div>
          ))}
        </div>
      )}

      <div className="flex-1 grid grid-cols-2 gap-4">
        {/* Visual Editor */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-3 border-b border-slate-700 text-sm font-medium text-slate-400">
            Visual Editor
          </div>
          <div className="h-[calc(100%-48px)]">
            <StateMachineCanvas config={yamlContent} />
          </div>
        </div>

        {/* YAML Editor */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-3 border-b border-slate-700 text-sm font-medium text-slate-400">
            YAML Configuration
          </div>
          <textarea
            value={yamlContent}
            onChange={(e) => setYamlContent(e.target.value)}
            className="w-full h-[calc(100%-48px)] p-4 bg-slate-900 text-white font-mono text-sm resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>
      </div>
    </div>
  )
}
