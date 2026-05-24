import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'
import { useAuthStore } from '../../stores/authStore'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { login, setUser } = useAuthStore()

  const onFinish = async (values: { id_card: string; password: string }) => {
    setLoading(true)
    try {
      const { data } = await apiClient.post('/api/auth/login/biz', values)
      login(data.access_token, data.refresh_token)
      const { data: user } = await apiClient.get('/api/auth/me')
      setUser(user)

      const routes: Record<string, string> = {
        front_desk: '/front-desk/rooms',
        manager: '/manager/dashboard',
        admin: '/admin',
      }
      navigate(routes[user.role] || '/login')
    } catch {
      message.error('登录失败，请检查身份证号和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#1A1A2E]">
      <div className="flex flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-2">🏨 智宿云 SmartStay</h1>
          <p className="text-white/60 text-sm">B端一体化管理后台</p>
        </div>
        <Card className="w-[380px] shadow-lg" styles={{ body: { padding: 32 } }}>
          <h2 className="text-lg font-semibold mb-6 text-center">用户登录</h2>
          <Form onFinish={onFinish} layout="vertical" size="large">
            <Form.Item name="id_card" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名（岗位拼音）" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item className="mb-0">
              <Button type="primary" htmlType="submit" block loading={loading} size="large">
                登 录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  )
}
