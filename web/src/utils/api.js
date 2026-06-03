const BASE = ''  // proxied via vite

export async function submitTailorJob({ resumeFile, jdFile, jdText }) {
  const form = new FormData()
  form.append('resume', resumeFile)
  if (jdFile) form.append('jd_file', jdFile)
  if (jdText) form.append('jd_text', jdText)

  const res = await fetch(`${BASE}/api/v1/tailor`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function getJobResult(jobId) {
  const res = await fetch(`${BASE}/api/v1/jobs/${jobId}/result`)
  if (!res.ok) throw new Error(`Failed to fetch result: ${res.status}`)
  return res.json()
}

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE}/api/v1/health`)
    if (!res.ok) return { status: 'error', ollama_connected: false }
    return res.json()
  } catch {
    return { status: 'error', ollama_connected: false }
  }
}

export function getDownloadUrl(jobId, type) {
  return `${BASE}/api/v1/jobs/${jobId}/download/${type}`
}
