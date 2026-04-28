import React, { useState, useEffect, useCallback } from 'react'
import AddUserForm from './components/AddUserForm'
import CatalogUpload from './components/CatalogUpload'
import ProductRegistration from './components/ProductRegistration'
import UserList from './components/UserList'
import Toast from './components/Toast'
import ConfirmDialog from './components/ConfirmDialog'

async function apiCall(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  // 204 No Content has no body
  if (res.status === 204) return null
  return res.json()
}

function App() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)          // { message, type }
  const [confirm, setConfirm] = useState(null)      // { message, onConfirm }

  const showToast = (message, type = 'success') => setToast({ message, type })
  const dismissToast = useCallback(() => setToast(null), [])

  const fetchUsers = useCallback(async () => {
    try {
      const data = await apiCall('/admin/users')
      setUsers(data.users ?? [])
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  const withConfirm = (message, action) =>
    setConfirm({ message, onConfirm: async () => { setConfirm(null); await action() } })

  const handleReroll = (userId) =>
    withConfirm("Reroll this user's API token? The new token will be emailed to them.", async () => {
      try {
        await apiCall(`/admin/users/${userId}/reroll`, { method: 'POST' })
        showToast('Token rerolled — new token sent to user.')
        fetchUsers()
      } catch (err) {
        showToast(err.message, 'error')
      }
    })

  const handleDisable = (userId) =>
    withConfirm('Disable this user?', async () => {
      try {
        await apiCall(`/admin/users/${userId}/disable`, { method: 'POST' })
        showToast('User disabled.')
        fetchUsers()
      } catch (err) {
        showToast(err.message, 'error')
      }
    })

  const handleReactivate = async (userId) => {
    try {
      await apiCall(`/admin/users/${userId}/reactivate`, { method: 'POST' })
      showToast('User reactivated — new token sent to user.')
      fetchUsers()
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  const handleDelete = (userId) =>
    withConfirm('Permanently delete this user? This cannot be undone.', async () => {
      try {
        await apiCall(`/admin/users/${userId}`, { method: 'DELETE' })
        showToast('User deleted.')
        fetchUsers()
      } catch (err) {
        showToast(err.message, 'error')
      }
    })

  return (
    <div className="app">
      <header>
        <h1>Gateway Admin</h1>
      </header>

      <main>
        <ProductRegistration onToast={showToast} />
        <CatalogUpload onSynced={(msg) => showToast(msg)} />
        <AddUserForm onUserCreated={(msg) => { showToast(msg); fetchUsers() }} />

        <section className="user-list">
          <h2>API Consumers</h2>
          {loading ? (
            <p className="loading">Loading…</p>
          ) : (
            <UserList
              users={users}
              onReroll={handleReroll}
              onDisable={handleDisable}
              onReactivate={handleReactivate}
              onDelete={handleDelete}
            />
          )}
        </section>
      </main>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={dismissToast} />
      )}

      {confirm && (
        <ConfirmDialog
          message={confirm.message}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

export default App
