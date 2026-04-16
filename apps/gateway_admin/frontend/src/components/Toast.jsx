import React, { useEffect } from 'react'

/**
 * Toast notification component.
 * @param {{ message: string, type: 'success'|'error', onClose: () => void }} props
 */
function Toast({ message, type = 'success', onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`toast toast-${type}`} role="alert" aria-live="polite">
      <span>{message}</span>
      <button className="toast-close" onClick={onClose} aria-label="Close notification">
        ×
      </button>
    </div>
  )
}

export default Toast
