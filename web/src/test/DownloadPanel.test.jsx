import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DownloadPanel } from '../components/DownloadPanel'

describe('DownloadPanel', () => {
  it('renders download heading', () => {
    render(<DownloadPanel jobId="test-job-123" />)
    expect(screen.getByText('Download Tailored Resume')).toBeInTheDocument()
  })

  it('renders DOCX download link', () => {
    render(<DownloadPanel jobId="test-job-123" />)
    const docxLink = screen.getByText(/Download DOCX/)
    expect(docxLink).toBeInTheDocument()
    expect(docxLink.closest('a')).toHaveAttribute(
      'href',
      '/api/v1/jobs/test-job-123/download/docx'
    )
  })

  it('renders PDF download link', () => {
    render(<DownloadPanel jobId="test-job-123" />)
    const pdfLink = screen.getByText(/Download PDF/)
    expect(pdfLink).toBeInTheDocument()
    expect(pdfLink.closest('a')).toHaveAttribute(
      'href',
      '/api/v1/jobs/test-job-123/download/pdf'
    )
  })

  it('DOCX link has correct download attribute', () => {
    render(<DownloadPanel jobId="job456" />)
    const docxLink = screen.getByText(/Download DOCX/).closest('a')
    expect(docxLink).toHaveAttribute('download', 'tailored_resume.docx')
  })

  it('PDF link has correct download attribute', () => {
    render(<DownloadPanel jobId="job456" />)
    const pdfLink = screen.getByText(/Download PDF/).closest('a')
    expect(pdfLink).toHaveAttribute('download', 'tailored_resume.pdf')
  })

  it('uses correct job id in links', () => {
    render(<DownloadPanel jobId="unique-job-xyz" />)
    const links = document.querySelectorAll('a')
    links.forEach(link => {
      if (link.href.includes('download')) {
        expect(link.href).toContain('unique-job-xyz')
      }
    })
  })
})
