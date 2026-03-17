import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Layout from './layout/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Pricing from './pages/Pricing'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Screener from './pages/Screener'
import NewsFeed from './pages/NewsFeed'
import Charts from './pages/Charts'
import TaxCenter from './pages/TaxCenter'
import Compliance from './pages/Compliance'
import Settings from './pages/Settings'
import TraderInbox from './pages/TraderInbox'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen bg-bg-base text-text-muted">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const { user, loading } = useAuth()

  return (
    <Routes>
      {/* Public pages */}
      <Route path="/landing" element={<PublicOnly><Landing /></PublicOnly>} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
      <Route path="/pricing" element={<Pricing />} />

      {/* Protected app */}
      <Route path="/*" element={
        <ProtectedRoute>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/screener" element={<Screener />} />
              <Route path="/news" element={<NewsFeed />} />
              <Route path="/charts" element={<Charts />} />
              <Route path="/tax" element={<TaxCenter />} />
              <Route path="/compliance" element={<Compliance />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/managed" element={<TraderInbox />} />
            </Routes>
          </Layout>
        </ProtectedRoute>
      } />
    </Routes>
  )
}
