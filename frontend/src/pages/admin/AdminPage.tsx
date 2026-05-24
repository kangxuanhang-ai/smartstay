import { Card, Button, Table, Tag, message, Space } from 'antd'
import apiClient from '../../api/client'

export default function AdminPage() {
  const handleSimulate = async (type: string) => {
    try {
      await apiClient.post(`/api/admin/simulate/${type}`)
      message.success('模拟事件已触发')
    } catch {
      message.error('模拟失败')
    }
  }

  const handleReset = async () => {
    try {
      await apiClient.post('/api/admin/reset')
      message.success('演示数据已重置')
    } catch {
      message.error('重置失败')
    }
  }

  const logColumns = [
    { title: '时间', dataIndex: 'time', key: 'time' },
    { title: '用户', dataIndex: 'user', key: 'user' },
    { title: '工具名称', dataIndex: 'tool', key: 'tool' },
    { title: '违规类型', dataIndex: 'violation', key: 'violation', render: (v: string) => <Tag color="red">{v}</Tag> },
    { title: '原始输入', dataIndex: 'input', key: 'input' },
  ]

  const logs = [
    { key: '1', time: '10:23:15', user: 'guest(302)', tool: 'modify_price', violation: 'ROLE_VIOLATION', input: '改成1元' },
    { key: '2', time: '10:25:01', user: 'guest(305)', tool: 'modify_price', violation: 'ROLE_VIOLATION', input: '免费' },
    { key: '3', time: '10:30:42', user: 'guest(301)', tool: 'control_ac', violation: 'PARAM_ABUSE', input: '温度999°' },
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

      <Card title="🛡️ 安全防御日志" className="mb-4">
        <Table columns={logColumns} dataSource={logs} pagination={false} size="small" />
      </Card>

      <Button danger block size="large" onClick={handleReset}>
        🔄 一键重置演示数据
      </Button>
    </div>
  )
}
