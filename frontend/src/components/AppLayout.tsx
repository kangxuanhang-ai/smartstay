import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button } from 'antd'
import {
  HomeOutlined, UnorderedListOutlined, DashboardOutlined,
  RobotOutlined, BookOutlined,
  UserOutlined, ToolOutlined, FileTextOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../stores/authStore'

const { Sider, Content, Header } = Layout

interface MenuItem {
  key: string
  icon: React.ReactNode
  label: string
  role: string
}

const allMenuItems: MenuItem[] = [
  { key: '/front-desk/rooms', icon: <HomeOutlined />, label: '房态格子图', role: 'front_desk' },
  { key: '/front-desk/work-orders', icon: <UnorderedListOutlined />, label: '工单看板', role: 'front_desk' },
  { key: '/manager/dashboard', icon: <DashboardOutlined />, label: '运营大盘', role: 'manager' },
  { key: '/manager/audit', icon: <RobotOutlined />, label: 'AI审计报告', role: 'manager' },
  { key: '/manager/knowledge', icon: <BookOutlined />, label: '知识库管理', role: 'manager' },
  { key: '/manager/users', icon: <UserOutlined />, label: '用户管理', role: 'manager' },
  { key: '/manager/invoices', icon: <FileTextOutlined />, label: '发票管理', role: 'manager' },
  { key: '/admin', icon: <ToolOutlined />, label: '管理沙盒', role: 'admin' },
]

const roleLabels: Record<string, string> = {
  front_desk: '前台',
  manager: '店长',
  admin: '管理',
}

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const menuItems = allMenuItems
    .filter((item) => item.role === user?.role)
    .map(({ key, icon, label }) => ({ key, icon, label }))

  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.key))?.key || ''

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Layout className="min-h-screen">
      <Sider width={220} theme="dark" breakpoint="lg" collapsedWidth={60}>
        <div className="flex items-center justify-center h-16 text-white text-lg font-bold bg-[#002140]">
          智宿云 · {roleLabels[user?.role || '']}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="bg-white flex items-center justify-between px-5 border-b border-gray-100">
          <span className="text-base font-semibold text-gray-900">
            🏨 SmartStay 酒店管理系统
          </span>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">👤 {user?.name}</span>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={handleLogout}
              className="text-gray-500 hover:text-red-500"
            >
              退出
            </Button>
          </div>
        </Header>
        <Content className="m-4 p-6 bg-white rounded-lg min-h-[calc(100vh-4rem)] overflow-auto">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
