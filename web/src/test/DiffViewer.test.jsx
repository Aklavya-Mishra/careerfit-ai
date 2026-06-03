import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiffViewer } from '../components/DiffViewer'

const sampleDiff = [
  {
    section: 'summary',
    original: 'Software engineer with 6 years Python experience.',
    tailored: 'Senior AI Systems Engineer with 6 years building LLM pipelines and MLOps systems.',
  },
  {
    section: 'skills',
    original: 'Python, Docker, Git',
    tailored: 'Python, Kubernetes, Docker, FastAPI, LLM orchestration, GCP, MLOps',
  },
]

const sampleGapReport = {
  overall_score: 0.74,
  missing_skills: ['vector databases', 'RAG', 'speech-to-text'],
  strong_sections: ['education'],
  weak_sections: ['summary'],
  section_scores: [],
}

describe('DiffViewer', () => {
  it('renders without crashing with empty diff', () => {
    render(<DiffViewer diff={[]} gapReport={null} />)
    expect(screen.getByText(/Changes Made/i)).toBeInTheDocument()
  })

  it('shows count of modified sections', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={null} />)
    expect(screen.getByText(/2 sections modified/i)).toBeInTheDocument()
  })

  it('shows singular when 1 section modified', () => {
    render(<DiffViewer diff={[sampleDiff[0]]} gapReport={null} />)
    expect(screen.getByText(/1 section modified/i)).toBeInTheDocument()
  })

  it('renders section names', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={null} />)
    expect(screen.getByText('summary')).toBeInTheDocument()
    expect(screen.getByText('skills')).toBeInTheDocument()
  })

  it('shows Modified badge for changed sections', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={null} />)
    const modifiedBadges = screen.getAllByText('Modified')
    expect(modifiedBadges.length).toBe(2)
  })

  it('shows original text in left panel', () => {
    render(<DiffViewer diff={[sampleDiff[0]]} gapReport={null} />)
    expect(screen.getByText(/Software engineer with 6 years Python/)).toBeInTheDocument()
  })

  it('shows tailored text in right panel', () => {
    render(<DiffViewer diff={[sampleDiff[0]]} gapReport={null} />)
    expect(screen.getByText(/Senior AI Systems Engineer/)).toBeInTheDocument()
  })

  it('shows Original and Tailored column headers', () => {
    render(<DiffViewer diff={[sampleDiff[0]]} gapReport={null} />)
    expect(screen.getByText('Original')).toBeInTheDocument()
    expect(screen.getByText('Tailored')).toBeInTheDocument()
  })

  it('collapses section on header click', () => {
    render(<DiffViewer diff={[sampleDiff[0]]} gapReport={null} />)
    // Click the section header to collapse
    const header = screen.getByText('summary').closest('div')
    fireEvent.click(header)
    // After collapse, original text should not be visible
    expect(screen.queryByText(/Software engineer with 6 years Python/)).not.toBeInTheDocument()
  })

  it('expands section on second click', () => {
    render(<DiffViewer diff={[sampleDiff[0]]} gapReport={null} />)
    const header = screen.getByText('summary').closest('div')
    fireEvent.click(header) // collapse
    fireEvent.click(header) // expand
    expect(screen.getByText(/Software engineer with 6 years Python/)).toBeInTheDocument()
  })

  it('renders gap report when provided', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={sampleGapReport} />)
    expect(screen.getByText('Gap Analysis Report')).toBeInTheDocument()
  })

  it('shows overall alignment score', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={sampleGapReport} />)
    expect(screen.getByText('74%')).toBeInTheDocument()
  })

  it('shows missing skills', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={sampleGapReport} />)
    expect(screen.getByText(/vector databases/)).toBeInTheDocument()
  })

  it('shows strong sections', () => {
    render(<DiffViewer diff={sampleDiff} gapReport={sampleGapReport} />)
    expect(screen.getByText(/education/)).toBeInTheDocument()
  })

  it('renders without gap report', () => {
    // Should not throw when gapReport is null
    const { container } = render(<DiffViewer diff={sampleDiff} gapReport={null} />)
    expect(container).toBeTruthy()
    expect(screen.queryByText('Gap Analysis Report')).not.toBeInTheDocument()
  })

  it('shows Unchanged badge for identical sections', () => {
    const sameDiff = [{ section: 'education', original: 'BITS Pilani', tailored: 'BITS Pilani' }]
    render(<DiffViewer diff={sameDiff} gapReport={null} />)
    expect(screen.getByText('Unchanged')).toBeInTheDocument()
  })
})
