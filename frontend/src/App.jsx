import { Routes, Route } from 'react-router-dom'
import Layout from './layout/Layout'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Screener from './pages/Screener'
import NewsFeed from './pages/NewsFeed'
import Charts from './pages/Charts'
import TaxCenter from './pages/TaxCenter'
import Compliance from './pages/Compliance'
import Settings from './pages/Settings'

export default function App() {
  return (
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
      </Routes>
    </Layout>
  )
}
