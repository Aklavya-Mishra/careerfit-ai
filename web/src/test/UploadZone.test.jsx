import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UploadZone } from '../components/UploadZone'

const DOCX_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const ACCEPT = '.pdf,.docx'

describe('UploadZone', () => {
  it('renders label text', () => {
    render(<UploadZone label="Upload Resume" accept={ACCEPT} file={null} onChange={() => {}} />)
    expect(screen.getByText('Upload Resume')).toBeInTheDocument()
  })

  it('shows drag instructions', () => {
    render(<UploadZone label="Upload Resume" accept={ACCEPT} file={null} onChange={() => {}} />)
    expect(screen.getByText(/Drag & drop/i)).toBeInTheDocument()
  })

  it('shows required asterisk when required prop is true', () => {
    render(<UploadZone label="Resume" accept={ACCEPT} file={null} onChange={() => {}} required />)
    expect(screen.getByText('*')).toBeInTheDocument()
  })

  it('shows filename when file is provided', () => {
    const file = new File(['content'], 'my_resume.docx', { type: DOCX_TYPE })
    render(<UploadZone label="Resume" accept={ACCEPT} file={file} onChange={() => {}} />)
    expect(screen.getByText('my_resume.docx')).toBeInTheDocument()
  })

  it('shows checkmark emoji when file is loaded', () => {
    const file = new File(['content'], 'resume.docx', { type: DOCX_TYPE })
    render(<UploadZone label="Resume" accept={ACCEPT} file={file} onChange={() => {}} />)
    expect(screen.getByText('✅')).toBeInTheDocument()
  })

  it('calls onChange when file is selected via input', async () => {
    const onChange = vi.fn()
    render(<UploadZone label="Resume" accept={ACCEPT} file={null} onChange={onChange} />)

    const input = document.querySelector('input[type="file"]')
    const file = new File(['content'], 'resume.docx', { type: DOCX_TYPE })

    await userEvent.upload(input, file)
    expect(onChange).toHaveBeenCalledWith(file)
  })

  it('calls onChange when file is dropped', () => {
    const onChange = vi.fn()
    const { container } = render(
      <UploadZone label="Resume" accept={ACCEPT} file={null} onChange={onChange} />
    )

    const zone = container.firstChild
    const file = new File(['content'], 'dropped.docx', { type: DOCX_TYPE })

    fireEvent.drop(zone, {
      dataTransfer: { files: [file] },
    })

    expect(onChange).toHaveBeenCalledWith(file)
  })

  it('does not call onChange on drop if no files', () => {
    const onChange = vi.fn()
    const { container } = render(
      <UploadZone label="Resume" accept={ACCEPT} file={null} onChange={onChange} />
    )

    const zone = container.firstChild
    fireEvent.drop(zone, { dataTransfer: { files: [] } })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('applies active style on drag over', () => {
    const { container } = render(
      <UploadZone label="Resume" accept={ACCEPT} file={null} onChange={() => {}} />
    )
    const zone = container.firstChild
    fireEvent.dragOver(zone, { preventDefault: () => {} })
    // Border color should change (borderColor set in state)
    expect(zone.style.borderColor).toBe('rgb(99, 102, 241)')
  })

  it('removes active style on drag leave', () => {
    const { container } = render(
      <UploadZone label="Resume" accept={ACCEPT} file={null} onChange={() => {}} />
    )
    const zone = container.firstChild
    fireEvent.dragOver(zone, { preventDefault: () => {} })
    fireEvent.dragLeave(zone)
    expect(zone.style.borderColor).not.toBe('rgb(99, 102, 241)')
  })
})
