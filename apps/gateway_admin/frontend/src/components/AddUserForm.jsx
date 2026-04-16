import React, { useState } from 'react'

/**
 * Form for creating a new API consumer.
 * On success calls onUserCreated(successMessage).
 */
function AddUserForm({ onUserCreated }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      let data
      try {
        data = await res.json()
      } catch {
        throw new Error(`Server error (${res.status}) — check server logs`)
      }
      if (!res.ok) throw new Error(data.detail || 'Failed to create user')

      setEmail('')
      onUserCreated?.(data.message || 'User created — token sent to email.')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="add-user-form">
      <h3>Add New User</h3>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="user@example.com"
          required
          disabled={loading}
          aria-label="Email address"
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Creating…' : 'Create User'}
        </button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  )
}

export default AddUserForm
