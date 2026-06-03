import { useState, useCallback } from 'react'
import { UploadZone } from '../components/UploadZone'
import { ProgressStream } from '../components/ProgressStream'
import { DiffViewer } from '../components/DiffViewer'
import { DownloadPanel } from '../components/DownloadPanel'
import { submitTailorJob } from '../utils/api'
import { useSSE } from '../hooks/useSSE'

const ACCEPT = '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'

function StatusBadge({ status }) {
  const map = {
    idle: ['#94a3b8', '●'],
    processing: ['#6366f1', '⟳'],
    complete: ['#22c55e', '✓'],
    error: ['#ef4444', '✕'],
  }
  const [color, icon] = map[status] || map.idle
  return (
    <span style={{ color, fontWeight: 600, fontSize: 13 }}>
      {icon} {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export function Home() {
  const [resumeFile, setResumeFile] = useState(null)
  const [jdFile, setJdFile] = useState(null)
  const [jdText, setJdText] = useState('')
  const [jdMode, setJdMode] = useState('file')  // 'file' | 'text'

  const [phase, setPhase] = useState('idle')  // idle | processing | complete | error
  const [jobId, setJobId] = useState(null)
  const [events, setEvents] = useState([])
  const [currentEvent, setCurrentEvent] = useState('')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleEvent = useCallback(({ event, data }) => {
    setEvents(ev => [...ev, { event, data }])
    setCurrentEvent(event)
    if (data.progress != null) setProgress(data.progress)
  }, [])

  const handleDone = useCallback((data) => {
    setPhase('complete')
    setProgress(100)
  }, [])

  const handleError = useCallback((msg) => {
    setPhase('error')
    setError(msg)
  }, [])

  useSSE(phase === 'processing' ? jobId : null, handleEvent, handleDone, handleError)

  const handleSubmit = async () => {
    if (!resumeFile) return
    if (jdMode === 'file' && !jdFile) return
    if (jdMode === 'text' && !jdText.trim()) return

    setPhase('processing')
    setEvents([])
    setProgress(0)
    setResult(null)
    setError(null)

    try {
      const { job_id } = await submitTailorJob({
        resumeFile,
        jdFile: jdMode === 'file' ? jdFile : null,
        jdText: jdMode === 'text' ? jdText : null,
      })
      setJobId(job_id)
    } catch (e) {
      setPhase('error')
      setError(e.message)
    }
  }

  const handleReset = () => {
    setPhase('idle')
    setJobId(null)
    setEvents([])
    setCurrentEvent('')
    setProgress(0)
    setResult(null)
    setError(null)
  }

  // Fetch result once SSE completes
  const handleFetchResult = useCallback(async () => {
    if (!jobId) return
    try {
      const data = await fetch(`/api/v1/jobs/${jobId}/result`).then(r => r.json())
      setResult(data.result)
    } catch {}
  }, [jobId])

  if (phase === 'complete' && !result && jobId) {
    handleFetchResult()
  }

  const canSubmit = resumeFile && (
    (jdMode === 'file' && jdFile) || (jdMode === 'text' && jdText.trim())
  )

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 20px' }}>
      {/* Header */}
      <div style={{ marginBottom: 32, textAlign: 'center' }}>
        <h1 style={{ fontSize: 32, fontWeight: 700, background: 'linear-gradient(135deg, #6366f1, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          careerfit-ai
        </h1>
        <p style={{ color: '#94a3b8', marginTop: 6 }}>
          AI-powered resume tailoring · Fully local · Powered by Ollama
        </p>
      </div>

      {/* Upload phase */}
      {phase === 'idle' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Your Resume</div>
              <UploadZone label="Upload Resume" accept={ACCEPT} file={resumeFile} onChange={setResumeFile} required />
            </div>
            <div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Job Description</div>
              {/* JD mode toggle */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                {['file', 'text'].map(m => (
                  <button key={m} onClick={() => setJdMode(m)} style={{
                    padding: '4px 14px', borderRadius: 20, border: 'none', fontSize: 12, fontWeight: 600,
                    background: jdMode === m ? '#6366f1' : '#2e3147',
                    color: jdMode === m ? 'white' : '#94a3b8', cursor: 'pointer',
                  }}>
                    {m === 'file' ? '📁 File' : '✏️ Paste'}
                  </button>
                ))}
              </div>
              {jdMode === 'file'
                ? <UploadZone label="Upload Job Description" accept={ACCEPT} file={jdFile} onChange={setJdFile} required />
                : <textarea
                    value={jdText}
                    onChange={e => setJdText(e.target.value)}
                    placeholder="Paste job description here..."
                    style={{
                      width: '100%', minHeight: 160, background: '#1a1d27',
                      border: '2px dashed #2e3147', borderRadius: 10, padding: 14,
                      color: '#e2e8f0', fontSize: 13, lineHeight: 1.6, resize: 'vertical',
                      outline: 'none', fontFamily: 'inherit',
                    }}
                  />
              }
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            style={{
              width: '100%', padding: '14px', borderRadius: 10, border: 'none',
              background: canSubmit ? '#6366f1' : '#2e3147',
              color: canSubmit ? 'white' : '#475569',
              fontSize: 15, fontWeight: 700, cursor: canSubmit ? 'pointer' : 'not-allowed',
              transition: 'background .2s',
            }}
          >
            ✨ Tailor My Resume
          </button>
        </div>
      )}

      {/* Processing phase */}
      {phase === 'processing' && (
        <ProgressStream events={events} currentEvent={currentEvent} progress={progress} />
      )}

      {/* Error phase */}
      {phase === 'error' && (
        <div style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 10, padding: 20, textAlign: 'center' }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>❌</div>
          <div style={{ color: '#ef4444', fontWeight: 600, marginBottom: 8 }}>Processing Failed</div>
          <div style={{ color: '#94a3b8', marginBottom: 16, fontSize: 13 }}>{error}</div>
          <button onClick={handleReset} style={{ padding: '8px 20px', background: '#6366f1', color: 'white', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>
            Try Again
          </button>
        </div>
      )}

      {/* Complete phase */}
      {phase === 'complete' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <StatusBadge status="complete" />
            <button onClick={handleReset} style={{ padding: '7px 16px', background: '#2e3147', color: '#e2e8f0', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', fontSize: 13 }}>
              ↩ Tailor Another
            </button>
          </div>

          {jobId && <DownloadPanel jobId={jobId} />}

          {result && (
            <DiffViewer diff={result.diff || []} gapReport={result.gap_report} />
          )}
        </div>
      )}
    </div>
  )
}
