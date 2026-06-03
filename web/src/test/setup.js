import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock EventSource globally (not available in jsdom)
global.EventSource = class EventSource {
  constructor(url) {
    this.url = url
    this.readyState = 0
    this._listeners = {}
    setTimeout(() => { this.readyState = 1 }, 0)
  }
  addEventListener(type, fn) {
    if (!this._listeners[type]) this._listeners[type] = []
    this._listeners[type].push(fn)
  }
  removeEventListener(type, fn) {
    if (this._listeners[type]) {
      this._listeners[type] = this._listeners[type].filter(f => f !== fn)
    }
  }
  close() { this.readyState = 2 }
  // Helper for tests: fire an event
  _emit(type, data) {
    const listeners = this._listeners[type] || []
    listeners.forEach(fn => fn({ data: typeof data === 'string' ? data : JSON.stringify(data) }))
  }
}

// Mock fetch globally
global.fetch = vi.fn()

// Suppress console.error for known React warnings in tests
const originalError = console.error
beforeEach(() => {
  console.error = (...args) => {
    if (typeof args[0] === 'string' && args[0].includes('Warning:')) return
    originalError(...args)
  }
})
afterEach(() => {
  console.error = originalError
  vi.clearAllMocks()
})
