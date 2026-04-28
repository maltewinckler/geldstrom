import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, afterEach } from 'vitest'
import ProductRegistration from './ProductRegistration'

// ─── Test 3.3 ─────────────────────────────────────────────────────────────────
// Validates: Requirement 3.3
describe('ProductRegistration – shows "not configured" message on 404', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('displays "not configured" message when GET /admin/product-registration returns 404', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Not found' }),
      })
    )

    render(<ProductRegistration />)

    await waitFor(() => {
      expect(
        screen.getByText('No product registration has been configured yet.')
      ).toBeInTheDocument()
    })
  })
})

// ─── Test 3.1 / 3.2 ──────────────────────────────────────────────────────────
// Validates: Requirements 3.1, 3.2
describe('ProductRegistration – displays product_key and product_version from API', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders product_key and product_version returned by GET /admin/product-registration', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            product_key: 'TEST-KEY',
            product_version: '1.0',
            updated_at: '2024-01-15T12:00:00Z',
          }),
      })
    )

    render(<ProductRegistration />)

    await waitFor(() => {
      expect(screen.getByText('TEST-KEY')).toBeInTheDocument()
    })

    expect(screen.getByText('1.0')).toBeInTheDocument()
  })
})

// ─── Test 3.4 ─────────────────────────────────────────────────────────────────
// Validates: Requirement 3.4
describe('ProductRegistration – form has product_key input, product_version input, and submit button', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders product_key input, product_version input, and submit button', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Not found' }),
      })
    )

    render(<ProductRegistration onToast={vi.fn()} />)

    // Wait for the initial fetch to complete
    await waitFor(() => {
      expect(screen.getByText('No product registration has been configured yet.')).toBeInTheDocument()
    })

    expect(screen.getByRole('textbox', { name: /product key/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /product version/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
  })
})

// ─── Test 3.5 ─────────────────────────────────────────────────────────────────
// Validates: Requirement 3.5
describe('ProductRegistration – successful PUT shows success toast and refreshes values', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls onToast with success message and displays refreshed values after successful PUT', async () => {
    const updatedRegistration = {
      product_key: 'NEW-KEY',
      product_version: '2.0',
      updated_at: '2024-06-01T10:00:00Z',
    }

    let callCount = 0
    vi.stubGlobal('fetch', (url, options) => {
      callCount++
      if (callCount === 1) {
        // Initial GET — 404
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: 'Not found' }),
        })
      }
      if (callCount === 2) {
        // PUT — success
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(updatedRegistration),
        })
      }
      // Refresh GET — returns updated values
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(updatedRegistration),
      })
    })

    const onToast = vi.fn()
    render(<ProductRegistration onToast={onToast} />)

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('No product registration has been configured yet.')).toBeInTheDocument()
    })

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /product key/i }), 'NEW-KEY')
    await user.type(screen.getByRole('textbox', { name: /product version/i }), '2.0')
    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(onToast).toHaveBeenCalledWith('Product registration updated.', 'success')
    })

    await waitFor(() => {
      expect(screen.getByText('NEW-KEY')).toBeInTheDocument()
      expect(screen.getByText('2.0')).toBeInTheDocument()
    })
  })
})

// ─── Test 3.6 ─────────────────────────────────────────────────────────────────
// Validates: Requirement 3.6
describe('ProductRegistration – failed PUT shows error toast with detail message', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls onToast with the error detail message when PUT returns 422', async () => {
    let callCount = 0
    vi.stubGlobal('fetch', () => {
      callCount++
      if (callCount === 1) {
        // Initial GET — 404
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: 'Not found' }),
        })
      }
      // PUT — 422 validation error
      return Promise.resolve({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: 'Product key must not be empty' }),
      })
    })

    const onToast = vi.fn()
    render(<ProductRegistration onToast={onToast} />)

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('No product registration has been configured yet.')).toBeInTheDocument()
    })

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /product key/i }), 'some-key')
    await user.type(screen.getByRole('textbox', { name: /product version/i }), '1.0')
    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(onToast).toHaveBeenCalledWith('Product key must not be empty', 'error')
    })
  })
})
