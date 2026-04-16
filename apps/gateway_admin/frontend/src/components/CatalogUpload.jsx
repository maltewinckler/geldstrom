import React, { useRef, useState } from 'react'

function CatalogUpload({ onSynced }) {
  const inputRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.csv')) {
      setError('Only .csv files are accepted.')
      return
    }

    setLoading(true)
    setError(null)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('/admin/catalog/sync', { method: 'POST', body: form })
      let data
      try { data = await res.json() } catch { throw new Error(`Server error (${res.status})`) }
      if (!res.ok) throw new Error(data.detail || 'Catalog sync failed')
      onSynced?.(`Catalog synced: ${data.loaded_count} institutes loaded, ${data.skipped_count} skipped.`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      // reset so the same file can be re-uploaded
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="catalog-upload">
      <h3>Institute Catalog</h3>
      <label className={`upload-btn${loading ? ' disabled' : ''}`}>
        {loading ? 'Uploading…' : 'Upload fints_institute.csv'}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={handleChange}
          disabled={loading}
          style={{ display: 'none' }}
        />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  )
}

export default CatalogUpload
