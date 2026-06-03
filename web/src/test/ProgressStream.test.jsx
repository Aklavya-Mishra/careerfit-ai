import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProgressStream } from '../components/ProgressStream'

const makeEvents = (eventNames) =>
  eventNames.map((event, i) => ({ event, data: { progress: i * 10 } }))

describe('ProgressStream', () => {
  it('renders "Processing" heading', () => {
    render(<ProgressStream events={[]} currentEvent="" progress={0} />)
    expect(screen.getByText('Processing')).toBeInTheDocument()
  })

  it('displays progress percentage', () => {
    render(<ProgressStream events={[]} currentEvent="" progress={42} />)
    expect(screen.getByText('42%')).toBeInTheDocument()
  })

  it('renders all pipeline steps', () => {
    render(<ProgressStream events={[]} currentEvent="" progress={0} />)
    expect(screen.getByText('Parsing resume')).toBeInTheDocument()
    expect(screen.getByText('Parsing job description')).toBeInTheDocument()
    expect(screen.getByText('Semantic gap analysis')).toBeInTheDocument()
    expect(screen.getByText('Rewriting sections')).toBeInTheDocument()
    expect(screen.getByText('Generating DOCX')).toBeInTheDocument()
    expect(screen.getByText('Generating PDF')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('shows 0% progress bar initially', () => {
    const { container } = render(
      <ProgressStream events={[]} currentEvent="" progress={0} />
    )
    // Find the progress bar fill div (second inner div)
    const bars = container.querySelectorAll('div[style*="width"]')
    const progressBar = Array.from(bars).find(el => el.style.width === '0%')
    expect(progressBar).toBeTruthy()
  })

  it('shows 100% progress when complete', () => {
    const { container } = render(
      <ProgressStream events={[]} currentEvent="complete" progress={100} />
    )
    const bars = container.querySelectorAll('div[style*="width: 100%"]')
    expect(bars.length).toBeGreaterThan(0)
  })

  it('shows active indicator for current event', () => {
    render(
      <ProgressStream
        events={makeEvents(['parsing_resume'])}
        currentEvent="parsing_resume"
        progress={10}
      />
    )
    // Active step should show "..." animation
    expect(screen.getByText(/\.\.\./)).toBeInTheDocument()
  })

  it('shows section name during rewriting', () => {
    const events = [
      { event: 'rewriting', data: { progress: 55, section: 'experience', step: '2/4' } },
    ]
    render(
      <ProgressStream events={events} currentEvent="rewriting" progress={55} />
    )
    expect(screen.getByText(/experience/)).toBeInTheDocument()
    expect(screen.getByText(/2\/4/)).toBeInTheDocument()
  })

  it('marks completed steps with checkmark', () => {
    render(
      <ProgressStream events={[]} currentEvent="analyzing_gaps" progress={35} />
    )
    // Steps before analyzing_gaps should show ✓
    const checkmarks = screen.getAllByText('✓')
    expect(checkmarks.length).toBeGreaterThan(0)
  })

  it('all steps show ✓ when complete', () => {
    render(
      <ProgressStream events={[]} currentEvent="complete" progress={100} />
    )
    const checkmarks = screen.getAllByText('✓')
    // All 7 steps should be marked done
    expect(checkmarks.length).toBe(7)
  })
})
