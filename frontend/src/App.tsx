import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import MainLayout from './components/Layout/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Cases from './pages/Cases'
import CaseDetail from './pages/CaseDetail'
import Borrowers from './pages/Borrowers'
import Campaigns from './pages/Campaigns'
import CampaignDetail from './pages/CampaignDetail'
import Reports from './pages/Reports'
import Communications from './pages/Communications'
import Settings from './pages/Settings'
import AuditLogs from './pages/AuditLogs'
import VoiceDemo from './pages/VoiceDemo'
import AICallTest from './pages/AICallTest'
import AIIntelligence from './pages/AIIntelligence'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          path="/"
          element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="cases" element={<Cases />} />
          <Route path="cases/:id" element={<CaseDetail />} />
          <Route path="borrowers" element={<Borrowers />} />
          <Route path="campaigns" element={<Campaigns />} />
          <Route path="campaigns/:id" element={<CampaignDetail />} />
          <Route path="communications" element={<Communications />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="audit-logs" element={<AuditLogs />} />
          <Route path="ai-intelligence" element={<AIIntelligence />} />
          <Route path="ai-demo" element={<VoiceDemo />} />
          <Route path="ai-call-test" element={<AICallTest />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
