import { useRef, useState } from 'react'

const styles = {
  zone: {
    border: '2px dashed #2e3147',
    borderRadius: 10,
    padding: '28px 20px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'border-color .2s, background .2s',
    background: '#1a1d27',
  },
  zoneActive: {
    borderColor: '#6366f1',
    background: '#1e2138',
  },
  zoneHasFile: {
    borderColor: '#22c55e',
    borderStyle: 'solid',
  },
  label: { fontSize: 13, color: '#94a3b8', marginTop: 6 },
  fileName: { fontSize: 13, color: '#22c55e', marginTop: 4, fontWeight: 500 },
  icon: { fontSize: 28, marginBottom: 6 },
}

export function UploadZone({ label, accept, file, onChange, required }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onChange(f)
  }

  const zoneStyle = {
    ...styles.zone,
    ...(dragging ? styles.zoneActive : {}),
    ...(file ? styles.zoneHasFile : {}),
  }

  return (
    <div
      style={zoneStyle}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <div style={styles.icon}>{file ? '✅' : '📄'}</div>
      <div style={{ color: file ? '#22c55e' : '#e2e8f0', fontWeight: 500 }}>
        {label}{required && <span style={{ color: '#ef4444' }}> *</span>}
      </div>
      <div style={styles.label}>Drag & drop or click to browse · PDF or DOCX</div>
      {file && <div style={styles.fileName}>{file.name}</div>}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={(e) => e.target.files[0] && onChange(e.target.files[0])}
      />
    </div>
  )
}
