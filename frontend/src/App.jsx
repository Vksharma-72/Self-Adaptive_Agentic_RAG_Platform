import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { Aurora } from './components/shell.jsx'
import Login from './pages/Login.jsx'
import Chat from './pages/Chat.jsx'
import Admin from './pages/admin/Admin.jsx'

function Protected({ children, adminOnly = false }) {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (adminOnly && !['admin', 'root'].includes(user.role)) return <Navigate to="/chat" replace />
  return children
}

export default function App() {
  return (
    <div className="h-full">
      <Aurora />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/chat"
          element={
            <Protected>
              <Chat />
            </Protected>
          }
        />
        <Route
          path="/admin"
          element={
            <Protected adminOnly>
              <Admin />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </div>
  )
}
