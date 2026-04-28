import React from 'react'

/**
 * Displays all users in a table sorted alphabetically by email.
 * Action buttons are rendered per-row based on user status.
 */
function UserList({ users, onReroll, onDisable, onReactivate, onDelete }) {
  if (users.length === 0) {
    return <p className="empty-state">No users found.</p>
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Email</th>
          <th>User ID</th>
          <th>Status</th>
          <th>Created</th>
          <th>Last Rotated</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map((user) => (
          <tr key={user.user_id}>
            <td>{user.email}</td>
            <td className="user-id">{user.user_id}</td>
            <td>
              <span className={`status status-${user.status}`}>{user.status}</span>
            </td>
            <td>{new Date(user.created_at).toLocaleDateString()}</td>
            <td>{user.rotated_at ? new Date(user.rotated_at).toLocaleDateString() : '—'}</td>
            <td className="actions">
              {user.status !== 'deleted' && (
                <button onClick={() => onReroll(user.user_id)}>Reroll</button>
              )}
              {user.status === 'active' && (
                <button onClick={() => onDisable(user.user_id)}>Disable</button>
              )}
              {user.status === 'disabled' && (
                <button onClick={() => onReactivate(user.user_id)}>Reactivate</button>
              )}
              <button className="btn-danger" onClick={() => onDelete(user.user_id)}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default UserList
