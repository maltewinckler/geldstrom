import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import CatalogUpload from './CatalogUpload'

// ─── Test 2.1 ────────────────────────────────────────────────────────────────
// Validates: Requirement 2.1
describe('CatalogUpload – file input attributes', () => {
  it('renders a file input with accept=".csv"', () => {
    render(<CatalogUpload />)
    const input = document.querySelector('input[type="file"]')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('accept', '.csv')
  })
})

// ─── Test 2.2 ────────────────────────────────────────────────────────────────
// Validates: Requirement 2.4
describe('CatalogUpload – loading state', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('disables the file input and shows a loading indicator while uploading', async () => {
    // fetch that never resolves — keeps the component in loading state
    vi.stubGlobal('fetch', () => new Promise(() => {}))

    render(<CatalogUpload />)

    const input = document.querySelector('input[type="file"]')
    const csvFile = new File(['a,b'], 'test.csv', { type: 'text/csv' })

    await userEvent.upload(input, csvFile)

    // Input should now be disabled
    expect(input).toBeDisabled()

    // Loading text should be visible in the label
    expect(screen.getByText('Uploading…')).toBeInTheDocument()
  })
})

// ─── Test 2.3 ────────────────────────────────────────────────────────────────
// Validates: Requirement 2.7
describe('CatalogUpload – input reset after upload completes', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('resets the file-input value after a successful upload', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ loaded_count: 5, skipped_count: 1 }),
      })
    )

    render(<CatalogUpload onSynced={() => {}} />)

    const input = document.querySelector('input[type="file"]')
    const csvFile = new File(['a,b'], 'test.csv', { type: 'text/csv' })

    await userEvent.upload(input, csvFile)

    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })

  it('resets the file-input value after a failed upload', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Catalog sync failed: db error' }),
      })
    )

    render(<CatalogUpload />)

    const input = document.querySelector('input[type="file"]')
    const csvFile = new File(['a,b'], 'test.csv', { type: 'text/csv' })

    await userEvent.upload(input, csvFile)

    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })
})

import * as fc from 'fast-check'

// ─── Property 4 ──────────────────────────────────────────────────────────────
// Validates: Requirements 2.2
// Feature: fints-institute-csv-upload, Property 4: non-CSV file selection shows error and suppresses fetch
describe('CatalogUpload – Property 4: non-CSV file selection shows error and suppresses fetch', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows an error and does not call fetch for any non-.csv filename', async () => {
    // Generate non-whitespace printable ASCII filenames that don't end in .csv
    const safeNonCsvFilename = fc
      .stringMatching(/^[!-~]+$/)
      .filter((name) => !name.endsWith('.csv'))

    await fc.assert(
      fc.asyncProperty(
        safeNonCsvFilename,
        async (filename) => {
          const fetchSpy = vi.fn()
          vi.stubGlobal('fetch', fetchSpy)

          const { unmount } = render(<CatalogUpload />)

          const input = document.querySelector('input[type="file"]')
          const nonCsvFile = new File(['data'], filename, { type: 'application/octet-stream' })

          // Use applyAccept: false so userEvent doesn't filter out non-.csv files
          // before they reach the component's own validation logic
          const user = userEvent.setup({ applyAccept: false })
          await user.upload(input, nonCsvFile)

          const errorEl = document.querySelector('[role="alert"]')
          const hasError = errorEl !== null && errorEl.textContent.length > 0
          const fetchNotCalled = fetchSpy.mock.calls.length === 0

          unmount()
          vi.restoreAllMocks()

          return hasError && fetchNotCalled
        }
      ),
      { numRuns: 100 }
    )
  })
})

// ─── Property 5 ──────────────────────────────────────────────────────────────
// Validates: Requirements 2.5
// Feature: fints-institute-csv-upload, Property 5: successful response displays loaded_count and skipped_count
describe('CatalogUpload – Property 5: successful response displays loaded_count and skipped_count', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('displays both loaded_count and skipped_count from a successful response', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.tuple(fc.nat(), fc.nat()),
        async ([loaded_count, skipped_count]) => {
          vi.stubGlobal('fetch', () =>
            Promise.resolve({
              ok: true,
              json: () => Promise.resolve({ loaded_count, skipped_count }),
            })
          )

          const messages = []
          const { unmount } = render(
            <CatalogUpload onSynced={(msg) => messages.push(msg)} />
          )

          const input = document.querySelector('input[type="file"]')
          const csvFile = new File(['a,b'], 'test.csv', { type: 'text/csv' })

          await userEvent.upload(input, csvFile)

          await waitFor(() => {
            expect(messages.length).toBeGreaterThan(0)
          })

          const message = messages[0]
          const containsLoaded = message.includes(String(loaded_count))
          const containsSkipped = message.includes(String(skipped_count))

          unmount()
          vi.restoreAllMocks()

          return containsLoaded && containsSkipped
        }
      ),
      { numRuns: 100 }
    )
  })
})

// ─── Property 6 ──────────────────────────────────────────────────────────────
// Validates: Requirements 2.6
// Feature: fints-institute-csv-upload, Property 6: error response detail is displayed to the user
describe('CatalogUpload – Property 6: error response detail is displayed to the user', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the error detail string from an error response', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1 }),
        async (errorString) => {
          vi.stubGlobal('fetch', () =>
            Promise.resolve({
              ok: false,
              status: 400,
              json: () => Promise.resolve({ detail: errorString }),
            })
          )

          const { unmount } = render(<CatalogUpload />)

          const input = document.querySelector('input[type="file"]')
          const csvFile = new File(['a,b'], 'test.csv', { type: 'text/csv' })

          await userEvent.upload(input, csvFile)

          await waitFor(() => {
            const errorEl = document.querySelector('[role="alert"]')
            expect(errorEl).toBeInTheDocument()
          })

          const errorEl = document.querySelector('[role="alert"]')
          const errorVisible = errorEl !== null && errorEl.textContent.includes(errorString)

          unmount()
          vi.restoreAllMocks()

          return errorVisible
        }
      ),
      { numRuns: 100 }
    )
  })
})
