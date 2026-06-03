import { describe, it, expect, vi, beforeEach } from 'vitest'
import { submitTailorJob, getJobResult, checkHealth, getDownloadUrl } from '../utils/api'

describe('api utils', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  describe('getDownloadUrl', () => {
    it('builds docx url correctly', () => {
      expect(getDownloadUrl('job123', 'docx')).toBe('/api/v1/jobs/job123/download/docx')
    })

    it('builds pdf url correctly', () => {
      expect(getDownloadUrl('job123', 'pdf')).toBe('/api/v1/jobs/job123/download/pdf')
    })

    it('uses job id in url', () => {
      const url = getDownloadUrl('abc-def-456', 'docx')
      expect(url).toContain('abc-def-456')
    })
  })

  describe('submitTailorJob', () => {
    it('sends POST to /api/v1/tailor', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'test-job-id', status: 'queued' }),
      })

      const file = new File(['content'], 'resume.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      })

      const result = await submitTailorJob({ resumeFile: file, jdText: 'Some JD' })

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/tailor',
        expect.objectContaining({ method: 'POST' })
      )
      expect(result.job_id).toBe('test-job-id')
    })

    it('throws on non-ok response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid file type' }),
      })

      const file = new File(['bad'], 'resume.txt', { type: 'text/plain' })
      await expect(submitTailorJob({ resumeFile: file, jdText: 'JD' }))
        .rejects.toThrow('Invalid file type')
    })

    it('includes jd_file in form data when provided', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'id1', status: 'queued' }),
      })

      const resumeFile = new File(['r'], 'resume.docx')
      const jdFile = new File(['jd'], 'jd.pdf')

      await submitTailorJob({ resumeFile, jdFile })

      const [, options] = global.fetch.mock.calls[0]
      const body = options.body
      expect(body).toBeInstanceOf(FormData)
    })

    it('includes jd_text in form data when provided', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'id2', status: 'queued' }),
      })

      const resumeFile = new File(['r'], 'resume.docx')
      await submitTailorJob({ resumeFile, jdText: 'We need a Python developer' })

      const [, options] = global.fetch.mock.calls[0]
      expect(options.body.get('jd_text')).toBe('We need a Python developer')
    })
  })

  describe('getJobResult', () => {
    it('fetches from correct url', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'abc', status: 'complete', result: {} }),
      })

      const result = await getJobResult('abc')
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/jobs/abc/result')
      expect(result.job_id).toBe('abc')
    })

    it('throws on error response', async () => {
      global.fetch.mockResolvedValueOnce({ ok: false, status: 404 })
      await expect(getJobResult('missing')).rejects.toThrow('404')
    })
  })

  describe('checkHealth', () => {
    it('returns health data on success', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok', ollama_connected: true }),
      })

      const result = await checkHealth()
      expect(result.status).toBe('ok')
      expect(result.ollama_connected).toBe(true)
    })

    it('returns error object on failure', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))
      const result = await checkHealth()
      expect(result.status).toBe('error')
      expect(result.ollama_connected).toBe(false)
    })
  })
})
