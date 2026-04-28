import React from 'react'

/**
 * Modal confirmation dialog.
 * @param {{ message: string, onConfirm: () => void, onCancel: () => void }} props
 */
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true">
      <div className="dialog">
        <p>{message}</p>
        <div className="dialog-actions">
          <button className="btn-danger" onClick={onConfirm}>Confirm</button>
          <button className="btn-secondary" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog
