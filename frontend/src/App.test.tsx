import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('CampusOps Scaffold Component', () => {
  it('renders the CampusOps heading', () => {
    render(<App />)
    const heading = screen.getByRole('heading', { level: 1, name: /campusops/i })
    expect(heading).toBeInTheDocument()
  })

  it('displays the scaffold notice that product workflows are not yet implemented', () => {
    render(<App />)
    expect(
      screen.getByText(/product workflows and operational features are not yet implemented/i),
    ).toBeInTheDocument()
  })
})
