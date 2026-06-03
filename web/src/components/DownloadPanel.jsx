import { getDownloadUrl } from '../utils/api'

export function DownloadPanel({ jobId }) {
  return (
    <div style={{
      background: '#1a1d27', border: '1px solid #2e3147', borderRadius: 10,
      padding: 20, marginBottom: 20,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 14 }}>Download Tailored Resume</div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <a
          href={getDownloadUrl(jobId, 'docx')}
          download="tailored_resume.docx"
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: '#6366f1', color: 'white',
            padding: '10px 20px', borderRadius: 8, textDecoration: 'none',
            fontWeight: 600, fontSize: 14, transition: 'background .2s',
          }}
          onMouseEnter={e => e.target.style.background = '#4f46e5'}
          onMouseLeave={e => e.target.style.background = '#6366f1'}
        >
          📄 Download DOCX
        </a>
        <a
          href={getDownloadUrl(jobId, 'pdf')}
          download="tailored_resume.pdf"
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: '#ef4444', color: 'white',
            padding: '10px 20px', borderRadius: 8, textDecoration: 'none',
            fontWeight: 600, fontSize: 14, transition: 'background .2s',
          }}
          onMouseEnter={e => e.target.style.background = '#dc2626'}
          onMouseLeave={e => e.target.style.background = '#ef4444'}
        >
          📋 Download PDF
        </a>
      </div>
    </div>
  )
}
