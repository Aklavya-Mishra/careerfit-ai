import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSSE } from '../hooks/useSSE'

// Track EventSource instances
let lastEventSource = null
const OriginalEventSource = global.EventSource

describe('useSSE hook', () => {
  beforeEach(() => {
    // Track created EventSource instances
    global.EventSource = class MockEventSource {
      constructor(url) {
        this.url = url
        this.readyState = 1
        this._listeners = {}
        lastEventSource = this
      }
      addEventListener(type, fn) {
        if (!this._listeners[type]) this._listeners[type] = []
        this._listeners[type].push(fn)
      }
      close() { this.readyState = 2; this._closed = true }
      _emit(type, data) {
        const listeners = this._listeners[type] || []
        listeners.forEach(fn => fn({ data: JSON.stringify(data) }))
      }
      _emitError() {
        if (this.onerror) this.onerror(new Error('connection error'))
      }
    }
  })

  afterEach(() => {
    global.EventSource = OriginalEventSource
    lastEventSource = null
  })

  it('does not create EventSource when jobId is null', () => {
    const onEvent = vi.fn()
    renderHook(() => useSSE(null, onEvent, vi.fn(), vi.fn()))
    expect(lastEventSource).toBeNull()
  })

  it('creates EventSource with correct URL when jobId provided', () => {
    renderHook(() => useSSE('job123', vi.fn(), vi.fn(), vi.fn()))
    expect(lastEventSource).not.toBeNull()
    expect(lastEventSource.url).toBe('/api/v1/jobs/job123/stream')
  })

  it('calls onEvent when SSE event fires', () => {
    const onEvent = vi.fn()
    renderHook(() => useSSE('job123', onEvent, vi.fn(), vi.fn()))

    act(() => {
      lastEventSource._emit('parsing_resume', { progress: 10 })
    })

    expect(onEvent).toHaveBeenCalledWith({
      event: 'parsing_resume',
      data: { progress: 10 },
    })
  })

  it('calls onDone when complete event fires', () => {
    const onDone = vi.fn()
    renderHook(() => useSSE('job123', vi.fn(), onDone, vi.fn()))

    act(() => {
      lastEventSource._emit('complete', { progress: 100, docx_url: '/download/docx' })
    })

    expect(onDone).toHaveBeenCalledWith({ progress: 100, docx_url: '/download/docx' })
  })

  it('calls onError when error event fires', () => {
    const onError = vi.fn()
    renderHook(() => useSSE('job123', vi.fn(), vi.fn(), onError))

    act(() => {
      lastEventSource._emit('error', { message: 'Pipeline failed' })
    })

    expect(onError).toHaveBeenCalledWith('Pipeline failed')
  })

  it('closes EventSource after complete event', () => {
    renderHook(() => useSSE('job123', vi.fn(), vi.fn(), vi.fn()))

    act(() => {
      lastEventSource._emit('complete', { progress: 100 })
    })

    expect(lastEventSource._closed).toBe(true)
  })

  it('closes EventSource after error event', () => {
    renderHook(() => useSSE('job123', vi.fn(), vi.fn(), vi.fn()))

    act(() => {
      lastEventSource._emit('error', { message: 'oops' })
    })

    expect(lastEventSource._closed).toBe(true)
  })

  it('calls onError on connection failure', () => {
    const onError = vi.fn()
    renderHook(() => useSSE('job123', vi.fn(), vi.fn(), onError))

    act(() => {
      lastEventSource._emitError()
    })

    expect(onError).toHaveBeenCalledWith('Connection lost')
  })

  it('closes EventSource on unmount', () => {
    const { unmount } = renderHook(() => useSSE('job123', vi.fn(), vi.fn(), vi.fn()))
    unmount()
    expect(lastEventSource._closed).toBe(true)
  })

  it('calls onEvent for all pipeline stages', () => {
    const onEvent = vi.fn()
    renderHook(() => useSSE('job123', onEvent, vi.fn(), vi.fn()))

    const stages = ['parsing_resume', 'parsing_jd', 'analyzing_gaps', 'generating_docx']
    act(() => {
      stages.forEach(stage => lastEventSource._emit(stage, { progress: 10 }))
    })

    expect(onEvent).toHaveBeenCalledTimes(stages.length)
  })
})
