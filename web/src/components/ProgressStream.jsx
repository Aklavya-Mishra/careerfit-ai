const STEPS = [
  { event: 'parsing_resume', label: 'Parsing resume' },
  { event: 'parsing_jd', label: 'Parsing job description' },
  { event: 'analyzing_gaps', label: 'Semantic gap analysis' },
  { event: 'rewriting', label: 'Rewriting sections' },
  { event: 'generating_docx', label: 'Generating DOCX' },
  { event: 'generating_pdf', label: 'Generating PDF' },
  { event: 'complete', label: 'Done' },
]

export function ProgressStream({ events, currentEvent, progress }) {
  const currentIdx = STEPS.findIndex(s => s.event === currentEvent)

  return (
    <div style={{ padding: '24px', background: '#1a1d27', borderRadius: 10, border: '1px solid #2e3147' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontWeight: 600 }}>Processing</span>
        <span style={{ color: '#6366f1', fontWeight: 600 }}>{progress}%</span>
      </div>

      {/* Progress bar */}
      <div style={{ background: '#2e3147', borderRadius: 4, height: 6, marginBottom: 20, overflow: 'hidden' }}>
        <div style={{
          width: `${progress}%`,
          height: '100%',
          background: 'linear-gradient(90deg, #6366f1, #818cf8)',
          borderRadius: 4,
          transition: 'width .4s ease',
        }} />
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {STEPS.map((step, idx) => {
          const done = idx < currentIdx || currentEvent === 'complete'
          const active = idx === currentIdx && currentEvent !== 'complete'
          const rewritingData = events.filter(e => e.event === 'rewriting').slice(-1)[0]

          return (
            <div key={step.event} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                background: done ? '#22c55e' : active ? '#6366f1' : '#2e3147',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, color: 'white', fontWeight: 600,
                boxShadow: active ? '0 0 0 3px rgba(99,102,241,.3)' : 'none',
                transition: 'all .3s',
              }}>
                {done ? '✓' : idx + 1}
              </div>
              <span style={{
                color: done ? '#22c55e' : active ? '#e2e8f0' : '#475569',
                fontWeight: active ? 600 : 400,
                fontSize: 13,
              }}>
                {step.label}
                {active && step.event === 'rewriting' && rewritingData?.data?.section &&
                  <span style={{ color: '#6366f1', marginLeft: 6 }}>
                    ({rewritingData.data.section} · {rewritingData.data.step})
                  </span>
                }
                {active && <span style={{ marginLeft: 6, animation: 'pulse 1.5s infinite' }}>...</span>}
              </span>
            </div>
          )
        })}
      </div>

      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
    </div>
  )
}
