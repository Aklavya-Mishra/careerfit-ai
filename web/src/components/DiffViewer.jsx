import { useState } from 'react'

function DiffSection({ section, original, tailored }) {
  const [expanded, setExpanded] = useState(true)

  const origLines = (original || '').split('\n')
  const newLines = (tailored || '').split('\n')
  const changed = original !== tailored

  return (
    <div style={{ border: '1px solid #2e3147', borderRadius: 8, overflow: 'hidden', marginBottom: 12 }}>
      <div
        onClick={() => setExpanded(e => !e)}
        style={{
          padding: '10px 14px',
          background: '#222536',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
          {section}
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 12, fontWeight: 600,
            background: changed ? 'rgba(99,102,241,.2)' : 'rgba(34,197,94,.2)',
            color: changed ? '#818cf8' : '#22c55e',
          }}>
            {changed ? 'Modified' : 'Unchanged'}
          </span>
          <span style={{ color: '#94a3b8', fontSize: 12 }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
          {/* Original */}
          <div style={{ borderRight: '1px solid #2e3147', padding: 14 }}>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Original</div>
            {origLines.map((line, i) => (
              <div key={i} style={{
                fontSize: 12, lineHeight: 1.6, color: '#94a3b8',
                padding: '1px 0',
                background: changed && line && !newLines.includes(line) ? 'rgba(239,68,68,.08)' : 'transparent',
                borderRadius: 3,
              }}>
                {line || <span style={{ opacity: 0 }}>_</span>}
              </div>
            ))}
          </div>

          {/* Tailored */}
          <div style={{ padding: 14 }}>
            <div style={{ fontSize: 11, color: '#6366f1', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tailored</div>
            {newLines.map((line, i) => (
              <div key={i} style={{
                fontSize: 12, lineHeight: 1.6, color: '#e2e8f0',
                padding: '1px 0',
                background: changed && line && !origLines.includes(line) ? 'rgba(99,102,241,.1)' : 'transparent',
                borderRadius: 3,
              }}>
                {line || <span style={{ opacity: 0 }}>_</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function DiffViewer({ diff, gapReport }) {
  return (
    <div>
      {/* Gap report summary */}
      {gapReport && (
        <div style={{
          background: '#1a1d27', border: '1px solid #2e3147', borderRadius: 10,
          padding: 16, marginBottom: 20,
        }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>Gap Analysis Report</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#6366f1' }}>
                {Math.round(gapReport.overall_score * 100)}%
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Alignment Score</div>
            </div>
            <div style={{ flex: 1 }}>
              {gapReport.missing_skills?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#f59e0b', fontWeight: 600 }}>Missing skills: </span>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>{gapReport.missing_skills.slice(0, 5).join(', ')}</span>
                </div>
              )}
              {gapReport.strong_sections?.length > 0 && (
                <div>
                  <span style={{ fontSize: 12, color: '#22c55e', fontWeight: 600 }}>Strong sections: </span>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>{gapReport.strong_sections.join(', ')}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Diffs */}
      <div style={{ fontWeight: 600, marginBottom: 12 }}>
        Changes Made
        <span style={{ fontWeight: 400, color: '#94a3b8', marginLeft: 8, fontSize: 13 }}>
          {diff.length} section{diff.length !== 1 ? 's' : ''} modified
        </span>
      </div>
      {diff.map((d) => (
        <DiffSection
          key={d.section}
          section={d.section}
          original={d.original}
          tailored={d.tailored}
        />
      ))}
    </div>
  )
}
