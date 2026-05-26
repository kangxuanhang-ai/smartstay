import { ConfigProvider } from 'antd'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import theme from './theme'
import ErrorBoundary from './components/ErrorBoundary'
import LoginPage from './pages/login/LoginPage'
import AuthGuard from './components/AuthGuard'
import AppLayout from './components/AppLayout'
import RoomGridPage from './pages/front-desk/RoomGridPage'
import WorkOrderBoard from './pages/front-desk/WorkOrderBoard'
import DashboardPage from './pages/manager/DashboardPage'
import AIAuditPage from './pages/manager/AIAuditPage'
import KnowledgeBasePage from './pages/manager/KnowledgeBasePage'
import UserManagementPage from './pages/manager/UserManagementPage'
import InvoiceManagementPage from './pages/manager/InvoiceManagementPage'
import AdminPage from './pages/admin/AdminPage'

export default function App() {
  return (
    <ErrorBoundary>
    <ConfigProvider theme={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AuthGuard><AppLayout /></AuthGuard>}>
            <Route path="/front-desk/rooms" element={<RoomGridPage />} />
            <Route path="/front-desk/work-orders" element={<WorkOrderBoard />} />
            <Route path="/manager/dashboard" element={<DashboardPage />} />
            <Route path="/manager/audit" element={<AIAuditPage />} />
            <Route path="/manager/knowledge" element={<KnowledgeBasePage />} />
            <Route path="/manager/users" element={<UserManagementPage />} />
            <Route path="/manager/invoices" element={<InvoiceManagementPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Route>
          <Route path="/" element={<Navigate to="/login" />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
    </ErrorBoundary>
  )
}
