import React, { useState, useEffect, useCallback } from 'react'

async function apiCall(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 404) return null
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

function ProductRegistration({ onToast }) {
  const [registration, setRegistration] = useState(undefined) // undefined = loading, null = not configured
  const [loading, setLoading] = useState(true)
  const [productKey, setProductKey] = useState('')
  const [productVersion, setProductVersion] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchRegistration = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiCall('/admin/product-registration')
      setRegistration(data) // null if 404, object if found
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [onToast])

  useEffect(() => { fetchRegistration() }, [fetchRegistration])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const res = await fetch('/admin/product-registration', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_key: productKey, product_version: productVersion }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(body.detail || `Request failed (${res.status})`)
      }
      onToast?.('Product registration updated.', 'success')
      await fetchRegistration()
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="product-registration">
      <h2>Product Registration</h2>
      {loading ? (
        <p className="loading">Loading…</p>
      ) : registration === null ? (
        <p className="not-configured">No product registration has been configured yet.</p>
      ) : registration ? (
        <dl className="registration-fields">
          <dt>Product Key</dt>
          <dd>{registration.product_key}</dd>
          <dt>Product Version</dt>
          <dd>{registration.product_version}</dd>
        </dl>
      ) : null}

      <form className="product-registration-form" onSubmit={handleSubmit}>
        <h3>Edit Product Registration</h3>
        <label>
          Product Key
          <input
            type="text"
            value={productKey}
            onChange={(e) => setProductKey(e.target.value)}
            placeholder="product_key"
            required
            disabled={submitting}
            aria-label="Product Key"
          />
        </label>
        <label>
          Product Version
          <input
            type="text"
            value={productVersion}
            onChange={(e) => setProductVersion(e.target.value)}
            placeholder="product_version"
            required
            disabled={submitting}
            aria-label="Product Version"
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save'}
        </button>
      </form>
    </section>
  )
}

export default ProductRegistration
