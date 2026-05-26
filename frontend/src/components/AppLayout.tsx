import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button } from 'antd'
import {
  HomeOutlined, UnorderedListOutlined, DashboardOutlined,
  RobotOutlined, BookOutlined,
  UserOutlined, ToolOutlined, FileTextOutlined,
  LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../stores/authStore'
import { useWebSocket } from '../hooks/useWebSocket'
import AIPricingAlert from '../pages/front-desk/AIPricingAlert'

const { Sider, Content, Header } = Layout

const allMenuItems = [
  { key: '/front-desk/rooms', icon: <HomeOutlined />, label: '房态格子图', role: 'front_desk' },
  { key: '/front-desk/work-orders', icon: <UnorderedListOutlined />, label: '工单看板', role: 'front_desk' },
  { key: '/manager/dashboard', icon: <DashboardOutlined />, label: '运营大盘', role: 'manager' },
  { key: '/manager/audit', icon: <RobotOutlined />, label: 'AI审计报告', role: 'manager' },
  { key: '/manager/knowledge', icon: <BookOutlined />, label: '知识库管理', role: 'manager' },
  { key: '/manager/users', icon: <UserOutlined />, label: '用户管理', role: 'manager' },
  { key: '/manager/invoices', icon: <FileTextOutlined />, label: '发票管理', role: 'manager' },
  { key: '/admin', icon: <ToolOutlined />, label: '管理沙盒', role: 'admin' },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const ws = useWebSocket()

  const [pricingOpen, setPricingOpen] = useState(false)
  const [pricingData, setPricingData] = useState({ logId: '', originalPrice: 0, suggestedPrice: 0, reason: '' })

  useEffect(() => {
    if (!user || user.role === 'admin') return
    const unsub = ws.on('ai_pricing.suggestion', (data) => {
      setPricingData({
        logId: data.log_id,
        originalPrice: data.original,
        suggestedPrice: data.suggested,
        reason: data.reason,
      })
      setPricingOpen(true)
    })
    return unsub
  }, [ws, user])

  const menuItems = allMenuItems
    .filter((item) => item.role === user?.role)
    .map(({ key, icon, label }) => ({ key, icon, label }))

  const selectedKey = menuItems.find((item) => location.pathname.startsWith(item.key))?.key || ''

  return (
    <Layout className="!h-screen !overflow-hidden">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        collapsedWidth={60}
        theme="dark"
        breakpoint="lg"
        onBreakpoint={(broken) => setCollapsed(broken)}
      >
        <div className="!flex !items-center !justify-center !h-16 !bg-[#002040] !overflow-hidden !whitespace-nowrap">
          <span className="!text-white !text-base !font-bold !tracking-wide">
            {collapsed ? '🏨' : '智宿云'}
          </span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout className="!flex !flex-col !flex-1 !min-w-0">
        <Header className="!flex !items-center !justify-between !bg-white !px-5 !border-b !border-slate-200" style={{ height: 56 }}>
          <div className="!flex !items-center !gap-3">
            <Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
            <span className="!text-base !font-semibold !text-slate-800 !hidden sm:!inline">
              🏨 SmartStay 酒店管理系统
            </span>
          </div>
          <div className="!flex !items-center !gap-3">
            <span className="!text-sm !text-slate-600">👤 {user?.name}</span>
            <Button type="text" icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login') }} className="!text-slate-600">
              <span className="!hidden sm:!inline">退出</span>
            </Button>
          </div>
        </Header>
        <Content className="!p-6 !bg-slate-50 !overflow-auto !flex-1">
          <div className="!bg-white !rounded-xl !shadow-sm !border !border-slate-200 !p-6 !min-h-full">
            <Outlet />
          </div>
        </Content>
      </Layout>

      <AIPricingAlert
        open={pricingOpen}
        logId={pricingData.logId}
        originalPrice={pricingData.originalPrice}
        suggestedPrice={pricingData.suggestedPrice}
        reason={pricingData.reason}
        onClose={() => setPricingOpen(false)}
      />
    </Layout>
  )
}
