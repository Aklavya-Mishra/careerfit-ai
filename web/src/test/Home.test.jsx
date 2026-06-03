import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Home } from '../pages/Home'

// Mock api module
vi.mock('../utils/api', () => ({
  submitTailorJob: vi.fn(),
  getJobResult: vi.fn(),
  checkHealth: vi.fn(),
  getDownloadUrl: vi.fn((jobId, type) => `/api/v1/jobs/${jobId}/download/${type}`),
}))

import { submitTailorJob, getJobResult } from '../utils/api'

const DOCX_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

describe('Home page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the app title', () => {
    render(<Home />)
    expect(screen.getByText('careerfit-ai')).toBeInTheDocument()
  })

  it('renders the tagline', () => {
    render(<Home />)
    expect(screen.getByText(/AI-powered resume tailoring/i)).toBeInTheDocument()
  })

  it('renders resume upload zone', () => {
    render(<Home />)
    expect(screen.getByText('Upload Resume')).toBeInTheDocument()
  })

  it('renders JD upload zone by default', () => {
    render(<Home />)
    expect(screen.getByText('Upload Job Description')).toBeInTheDocument()
  })

  it('shows JD paste mode when Paste button clicked', async () => {
    render(<Home />)
    const pasteBtn = screen.getByText(/Paste/i)
    await userEvent.click(pasteBtn)
    expect(screen.getByPlaceholderText(/Paste job description here/i)).toBeInTheDocument()
  })

  it('shows File upload mode when File button clicked', async () => {
    render(<Home />)
    // Switch to paste
    await userEvent.click(screen.getByText(/Paste/i))
    // Switch back to file
    await userEvent.click(screen.getByText(/File/i))
    expect(screen.getByText('Upload Job Description')).toBeInTheDocument()
  })

  it('submit button is disabled initially', () => {
    render(<Home />)
    const btn = screen.getByText(/Tailor My Resume/i)
    expect(btn).toBeDisabled()
  })

  it('submit button stays disabled with only resume uploaded', async () => {
    render(<Home />)
    const input = document.querySelector('input[type="file"]')
    const file = new File(['content'], 'resume.docx', { type: DOCX_TYPE })
    await userEvent.upload(input, file)
    // JD still missing
    const btn = screen.getByText(/Tailor My Resume/i)
    expect(btn).toBeDisabled()
  })

  it('submit button enables when resume + JD text provided', async () => {
    render(<Home />)

    // Upload resume
    const resumeInput = document.querySelectorAll('input[type="file"]')[0]
    const file = new File(['content'], 'resume.docx', { type: DOCX_TYPE })
    await userEvent.upload(resumeInput, file)

    // Switch to paste mode and type JD
    await userEvent.click(screen.getByText(/Paste/i))
    const textarea = screen.getByPlaceholderText(/Paste job description/i)
    await userEvent.type(textarea, 'Senior AI Engineer required')

    const btn = screen.getByText(/Tailor My Resume/i)
    expect(btn).not.toBeDisabled()
  })

  it('shows processing UI after submit', async () => {
    submitTailorJob.mockResolvedValueOnce({ job_id: 'test-job-001', status: 'queued' })

    render(<Home />)

    const resumeInput = document.querySelectorAll('input[type="file"]')[0]
    await userEvent.upload(resumeInput, new File(['c'], 'r.docx', { type: DOCX_TYPE }))
    await userEvent.click(screen.getByText(/Paste/i))
    await userEvent.type(screen.getByPlaceholderText(/Paste job description/i), 'JD text here')

    await userEvent.click(screen.getByText(/Tailor My Resume/i))

    await waitFor(() => {
      expect(screen.getByText('Processing')).toBeInTheDocument()
    })
  })

  it('shows error state when submit fails', async () => {
    submitTailorJob.mockRejectedValueOnce(new Error('Server unavailable'))

    render(<Home />)

    const resumeInput = document.querySelectorAll('input[type="file"]')[0]
    await userEvent.upload(resumeInput, new File(['c'], 'r.docx', { type: DOCX_TYPE }))
    await userEvent.click(screen.getByText(/Paste/i))
    await userEvent.type(screen.getByPlaceholderText(/Paste job description/i), 'JD')

    await userEvent.click(screen.getByText(/Tailor My Resume/i))

    await waitFor(() => {
      expect(screen.getByText(/Processing Failed/i)).toBeInTheDocument()
      expect(screen.getByText(/Server unavailable/i)).toBeInTheDocument()
    })
  })

  it('shows Try Again button in error state', async () => {
    submitTailorJob.mockRejectedValueOnce(new Error('Error'))

    render(<Home />)
    const resumeInput = document.querySelectorAll('input[type="file"]')[0]
    await userEvent.upload(resumeInput, new File(['c'], 'r.docx', { type: DOCX_TYPE }))
    await userEvent.click(screen.getByText(/Paste/i))
    await userEvent.type(screen.getByPlaceholderText(/Paste job description/i), 'JD')
    await userEvent.click(screen.getByText(/Tailor My Resume/i))

    await waitFor(() => {
      expect(screen.getByText(/Try Again/i)).toBeInTheDocument()
    })
  })

  it('resets to idle state when Try Again is clicked', async () => {
    submitTailorJob.mockRejectedValueOnce(new Error('Error'))

    render(<Home />)
    const resumeInput = document.querySelectorAll('input[type="file"]')[0]
    await userEvent.upload(resumeInput, new File(['c'], 'r.docx', { type: DOCX_TYPE }))
    await userEvent.click(screen.getByText(/Paste/i))
    await userEvent.type(screen.getByPlaceholderText(/Paste job description/i), 'JD')
    await userEvent.click(screen.getByText(/Tailor My Resume/i))

    await waitFor(() => screen.getByText(/Try Again/i))
    await userEvent.click(screen.getByText(/Try Again/i))

    expect(screen.getByText('careerfit-ai')).toBeInTheDocument()
    expect(screen.getByText(/Tailor My Resume/i)).toBeInTheDocument()
  })
})
