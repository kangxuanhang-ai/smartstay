import { useEffect, useState } from 'react'
import { Card, Button, Table, Tag, message, Space } from 'antd'
import apiClient from '../../api/client'

interface SecurityLog {
  id: string
  user_id: string
  room_id: string | null
  role: string
  tool_name: string
  tool_params: Record<string, unknown> | null
  violation_type: string
  user_input: string | null
  intercepted_at: string
}

export default function AdminPage() {
  const [logs, setLogs] = useState<SecurityLog[]>([])
  const [loading, setLoading] = useState(false)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/api/admin/safety-logs')
      setLogs(data.map((l: SecurityLog, i: number) => ({ ...l, key: String(i) })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, [])

  const handleSimulate = async (type: string) => {
    try {
      await apiClient.post(`/api/admin/simulate/${type}`)
      message.success('模拟事件已触发')
      fetchLogs()
    } catch {
      message.error('模拟失败')
    }
  }

  const handleReset = async () => {
    try {
      await apiClient.post('/api/admin/reset')
      message.success('演示数据已重置')
      fetchLogs()
    } catch {
      message.error('重置失败')
    }
  }

  const handleSeedMock = async () => {
    try {
      const { data } = await apiClient.post('/api/admin/seed-mock')
      message.success(data.message || 'Mock数据已注入')
      fetchLogs()
    } catch {
      message.error('注入失败')
    }
  }

  const logColumns = [
    { title: '时间', dataIndex: 'intercepted_at', key: 'time', width: 90, render: (v: string) => new Date(v).toLocaleTimeString('zh-CN') },
    { title: '用户角色', dataIndex: 'role', key: 'role', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    { title: '工具名称', dataIndex: 'tool_name', key: 'tool', width: 160 },
    { title: '违规类型', dataIndex: 'violation_type', key: 'violation', width: 120, render: (v: string) => <Tag color="red">{v}</Tag> },
    { title: '原始输入', dataIndex: 'user_input', key: 'input', ellipsis: true },
  ]

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">🔧 系统管理沙盒</h2>

      <Card title="🔬 物理环境事件一键模拟器" className="mb-4">
        <Space direction="vertical" className="w-full">
          <Button type="primary" block onClick={() => handleSimulate('door-open')}>
            🚪 模拟 302 房智能门锁首次被物理打开 → 订单推进 CHECKED_IN
          </Button>
          <Button block style={{ background: '#FAAD14', color: '#fff', borderColor: '#FAAD14' }} onClick={() => handleSimulate('event')}>
            🎵 模拟突发外部舆情：周杰伦演唱会 → 观察AI定价弹窗
          </Button>
          <Button block danger onClick={() => handleSimulate('prompt-inject')}>
            🛡️ 模拟恶意 Prompt 注入攻击 → 观察Guard拦截日志
          </Button>
        </Space>
      </Card>

      <Card title={`🛡️ 安全防御日志 (${logs.length})`} className="mb-4">
        <Table columns={logColumns} dataSource={logs} loading={loading} pagination={{ pageSize: 10 }} size="small" />
      </Card>

      <Button block size="large" style={{ background: '#1677FF', color: '#fff', borderColor: '#1677FF', marginBottom: 12 }}
        onClick={handleSeedMock}>
        📦 批量注入 Mock 演示数据（10住客 + 5订单 + 20消费）
      </Button>

      <Button danger block size="large" onClick={handleReset}>
        🔄 一键重置演示数据
      </Button>
    </div>
  )
}
