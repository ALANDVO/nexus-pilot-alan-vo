import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listParts, uploadPart, deletePart, startUnfold, getUnfoldResult, downloadUnfoldProfile, downloadUnfoldBendLines } from '@/api/client'
import { usePartsStore, useUnfoldStore } from '@/types/api'
import { useAuth } from '@/hooks/useAuth'

export function Dashboard() {
  const { user, isAuthenticated, logout, checkAuth } = useAuth()
  const navigate = useNavigate()
  const { parts, setParts, setLoading, setError, addPart, removePart } = usePartsStore()
  const { jobs, setJob } = useUnfoldStore()

  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [showUnfoldModal, setShowUnfoldModal] = useState<{ partId: number; partName: string } | null>(null)
  const [unfoldParams, setUnfoldParams] = useState({ kFactor: 0.33, kerf: 0.0 })

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    loadParts()
  }, [isAuthenticated, navigate])

  const loadParts = async () => {
    setLoading(true)
    try {
      const data = await listParts()
      setParts(data.parts)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load parts')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.step') && !file.name.endsWith('.stp')) {
      setError('Only .step and .stp files are supported')
      return
    }

    setUploading(true)
    setUploadProgress(0)
    try {
      const part = await uploadPart(file, setUploadProgress)
      addPart(part)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(0)
      event.currentTarget.value = ''
    }
  }

  const handleDeletePart = async (partId: number) => {
    if (!confirm('Delete this part?')) return
    try {
      await deletePart(partId)
      removePart(partId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const handleStartUnfold = async () => {
    if (!showUnfoldModal) return
    try {
      const result = await startUnfold(showUnfoldModal.partId, unfoldParams.kFactor, unfoldParams.kerf)
      setJob({ ...result, part_id: showUnfoldModal.partId } as any)
      setShowUnfoldModal(null)
      loadParts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unfold failed')
    }
  }

  const handleDownloadProfile = async (partId: number, jobId: number) => {
    try {
      await downloadUnfoldProfile(partId, jobId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed')
    }
  }

  const handleDownloadBendLines = async (partId: number, jobId: number) => {
    try {
      await downloadUnfoldBendLines(partId, jobId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed')
    }
  }

  const getPartJob = (partId: number) => {
    return Object.values(jobs).find(j => j.part_id === partId)
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      ready: 'badge-success',
      processing: 'badge-warning',
      uploaded: 'badge-info',
      failed: 'badge-error',
      pending: 'badge-info',
      running: 'badge-warning',
      completed: 'badge-success',
    }
    return variants[status] || 'badge-info'
  }

  if (!isAuthenticated) return null

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="container px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-900">nexus-pilot</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">{user?.email}</span>
            <button onClick={logout} className="btn btn-secondary text-sm">Logout</button>
          </div>
        </div>
      </header>

      <main className="container px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">✕</button>
          </div>
        )}

        <div className="mb-8">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Upload STEP File</h2>
          <div className="card">
            <input
              type="file"
              accept=".step,.stp"
              onChange={handleFileUpload}
              disabled={uploading}
              className="mb-4"
            />
            {uploading && (
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Uploading...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 transition-all" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}
            <p className="text-sm text-slate-500">Maximum file size: 500 MB</p>
          </div>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Your Parts</h2>
          {loading ? (
            <div className="card text-center py-8 text-slate-500">Loading...</div>
          ) : parts.length === 0 ? (
            <div className="card text-center py-8 text-slate-500">
              No parts uploaded yet. Upload a STEP file to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {parts.map((part) => {
                const job = getPartJob(part.id)
                return (
                  <div key={part.id} className="card flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-slate-900 truncate">{part.original_filename}</h3>
                        <span className={`badge ${getStatusBadge(part.status)}`}>{part.status}</span>
                      </div>
                      <p className="text-sm text-slate-500 mt-1">
                        {(part.file_size / 1024).toFixed(1)} KB • {new Date(part.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                      {part.status === 'ready' && (
                        <>
                          <button
                            onClick={() => setShowUnfoldModal({ partId: part.id, partName: part.original_filename })}
                            className="btn btn-primary text-sm"
                            disabled={job?.status === 'running' || job?.status === 'pending'}
                          >
                            {job?.status === 'running' ? 'Unfolding...' : job?.status === 'pending' ? 'Queued' : 'Unfold'}
                          </button>
                        </>
                      )}

                      {job && job.status === 'completed' && job.result && (
                        <>
                          <button
                            onClick={() => handleDownloadProfile(part.id, job.id)}
                            className="btn btn-secondary text-sm"
                          >
                            Download Profile
                          </button>
                          <button
                            onClick={() => handleDownloadBendLines(part.id, job.id)}
                            className="btn btn-secondary text-sm"
                          >
                            Download Bend Lines
                          </button>
                        </>
                      )}

                      <button
                        onClick={() => handleDeletePart(part.id)}
                        className="btn btn-danger text-sm"
                      >
                        Delete
                      </button>
                    </div>

                    {job && job.status !== 'pending' && (
                      <div className="w-full md:w-auto md:flex md:items-center gap-4 pt-4 border-t border-slate-200">
                        <div className="flex items-center gap-4 text-sm">
                          <span className={`badge ${getStatusBadge(job.status)}`}>{job.status}</span>
                          {job.result && (
                            <>
                              <span>Bends: {job.result.bend_count}</span>
                              <span>Area: {job.result.blank_area.toFixed(1)} mm²</span>
                              <span>Vol. conservation: {(job.result.volume_conservation_ratio * 100).toFixed(1)}%</span>
                            </>
                          )}
                          {job.error_message && (
                            <span className="text-red-600">Error: {job.error_message}</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </main>

      {showUnfoldModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">Unfold {showUnfoldModal.partName}</h3>
            <div className="space-y-4">
              <div>
                <label className="label">K-Factor</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={unfoldParams.kFactor}
                  onChange={(e) => setUnfoldParams({ ...unfoldParams, kFactor: parseFloat(e.target.value) })}
                  className="input"
                />
                <p className="text-xs text-slate-500 mt-1">Typical range: 0.3–0.5 (0.33 default)</p>
              </div>
              <div>
                <label className="label">Kerf (mm)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={unfoldParams.kerf}
                  onChange={(e) => setUnfoldParams({ ...unfoldParams, kerf: parseFloat(e.target.value) })}
                  className="input"
                />
                <p className="text-xs text-slate-500 mt-1">Laser/waterjet kerf compensation</p>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button onClick={() => setShowUnfoldModal(null)} className="btn btn-secondary">Cancel</button>
                <button onClick={handleStartUnfold} className="btn btn-primary">Start Unfold</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}