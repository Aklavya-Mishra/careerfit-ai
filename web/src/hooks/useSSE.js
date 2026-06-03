import { useEffect, useRef, useCallback } from 'react'

export function useSSE(jobId, onEvent, onDone, onError) {
  const esRef = useRef(null)

  const connect = useCallback(() => {
    if (!jobId) return
    const es = new EventSource(`/api/v1/jobs/${jobId}/stream`)
    esRef.current = es
    let terminated = false

    const EVENTS = [
      'queued', 'parsing_resume', 'parsing_jd', 'analyzing_gaps',
      'rewriting', 'generating_docx', 'generating_pdf', 'complete', 'error'
    ]

    EVENTS.forEach(evt => {
      es.addEventListener(evt, (e) => {
        const data = JSON.parse(e.data || '{}')
        onEvent({ event: evt, data })
        if (evt === 'complete' || evt === 'error') {
          terminated = true
          es.close()
          if (evt === 'complete') onDone(data)
          else onError(data.message || 'Unknown error')
        }
      })
    })

    es.addEventListener('done', () => { terminated = true; es.close() })
    es.onerror = () => {
      if (terminated) return
      es.close()
      onError('Connection lost')
    }
  }, [jobId])

  useEffect(() => {
    connect()
    return () => esRef.current?.close()
  }, [connect])
}
