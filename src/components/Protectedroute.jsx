// src/components/ProtectedRoute.jsx
import { Navigate, useLocation } from 'react-router-dom'
import { isLoggedIn } from '../auth'

export default function ProtectedRoute({ children }) {
  const location = useLocation()

  if (!isLoggedIn()) {
    // `replace` keeps the guarded page out of the back-button history.
    // `state.from` lets the login page send them back where they were headed.
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}