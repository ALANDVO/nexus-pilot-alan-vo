import { useState, useCallback } from 'react'

export interface ModelComponent {
  index: number
  name: string
  volume: number
  faceCount: number
  loadable: boolean
  estimatedMemoryMb: number
}

export interface LoadPlan {
  loadable: ModelComponent[]
  skipped: ModelComponent[]
  estimatedMemoryMb: number
  envelopeMb: number
}

export function ModelLoader() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadPlan, setLoadPlan] = useState<LoadPlan | null>(null)
  const [selectedComponents, setSelectedComponents] = useState<Set<number>>(new Set())

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setLoadPlan(null)
      setSelectedComponents(new Set())
    }
  }, [])

  const analyzeFile = useCallback(async () => {
    if (!file) return
    setLoading(true)
    try {
      // In real implementation, would call backend /api/parts/analyze
      // For now, simulate
      await new Promise(r => setTimeout(r, 1000))
      const mockComponents: ModelComponent[] = [
        { index: 0, name: 'Base_Plate', volume: 50000, faceCount: 12, loadable: true, estimatedMemoryMb: 12 },
        { index: 1, name: 'Side_Wall_1', volume: 15000, faceCount: 8, loadable: true, estimatedMemoryMb: 8 },
        { index: 2, name: 'Side_Wall_2', volume: 15000, faceCount: 8, loadable: true, estimatedMemoryMb: 8 },
        { index: 3, name: 'Rib_1', volume: 2000, faceCount: 6, loadable: true, estimatedMemoryMb: 4 },
        { index: 4, name: 'Rib_2', volume: 2000, faceCount: 6, loadable: true, estimatedMemoryMb: 4 },
        { index: 5, name: 'Boss_1', volume: 500, faceCount: 24, loadable: true, estimatedMemoryMb: 10 },
        { index: 6, name: 'Boss_2', volume: 500, faceCount: 24, loadable: true, estimatedMemoryMb: 10 },
        { index: 7, name: 'Large_Assembly', volume: 100000, faceCount: 5000, loadable: false, estimatedMemoryMb: 500 },
      ]
      const envelopeMb = 100
      let currentMb = 0
      const loadable: ModelComponent[] = []
      const skipped: ModelComponent[] = []
      mockComponents.forEach(c => {
        if (currentMb + c.estimatedMemoryMb <= envelopeMb && c.loadable) {
          loadable.push({ ...c, loadable: true })
          currentMb += c.estimatedMemoryMb
        } else {
          skipped.push({ ...c, loadable: false })
        }
      })
      setLoadPlan({ loadable, skipped, estimatedMemoryMb: currentMb, envelopeMb })
      // Auto-select loadable
      setSelectedComponents(new Set(loadable.map(c => c.index)))
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [file])

  const toggleComponent = useCallback((index: number) => {
    setSelectedComponents(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }, [])

  const loadSelected = useCallback(async () => {
    // Would call backend to load selected components
    console.log('Loading components:', Array.from(selectedComponents))
  }, [selectedComponents])

  if (!file) {
    return (
      <div className="card p-8 text-center">
        <input
          type="file"
          accept=".step,.stp"
          onChange={handleFileChange}
          className="mb-4"
        />
        <p className="text-slate-500">Select a STEP file to analyze</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="font-medium">{file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)</h3>
        <button
          onClick={analyzeFile}
          disabled={loading}
          className="btn btn-primary mt-2"
        >
          {loading ? 'Analyzing...' : 'Analyze Components'}
        </button>
      </div>

      {loadPlan && (
        <div>
          <div className="mb-3 flex items-center justify-between text-sm">
            <span>Memory: {loadPlan.estimatedMemoryMb} / {loadPlan.envelopeMb} MB</span>
            <div className="h-2 w-48 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all"
                style={{ width: `${(loadPlan.estimatedMemoryMb / loadPlan.envelopeMb) * 100}%` }}
              />
            </div>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {[
              { label: 'Loadable', components: loadPlan.loadable, defaultSelected: true },
              { label: 'Skipped (exceeds envelope)', components: loadPlan.skipped, defaultSelected: false }
            ].map(({ label, components, defaultSelected }) => (
              <div key={label} className="border-t border-slate-200 pt-3">
                <h4 className="text-sm font-medium text-slate-500 mb-2">{label} ({components.length})</h4>
                {components.map(comp => (
                  <label key={comp.index} className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded">
                    <input
                      type="checkbox"
                      checked={selectedComponents.has(comp.index)}
                      onChange={() => toggleComponent(comp.index)}
                      disabled={!comp.loadable}
                      className="rounded border-slate-300"
                    />
                    <span className="text-sm font-medium">{comp.name}</span>
                    <span className="text-xs text-slate-500 ml-auto">
                      {comp.faceCount} faces • ~{comp.estimatedMemoryMb} MB
                    </span>
                  </label>
                ))}
              </div>
            ))}

            <button
              onClick={loadSelected}
              disabled={selectedComponents.size === 0}
              className="btn btn-primary w-full mt-4"
            >
              Load Selected ({selectedComponents.size})
            </button>
          </div>
        </div>
      )}
    </div>
  )
}