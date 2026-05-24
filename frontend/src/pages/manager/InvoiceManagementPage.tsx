import { Table, Tag, Space, Button, Tabs } from 'antd'

const columns = [
  { title: '房间', dataIndex: 'room', key: 'room' },
  { title: '公司抬头', dataIndex: 'company', key: 'company' },
  { title: '税号', dataIndex: 'tax_id', key: 'tax_id' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => {
    const colors: Record<string, string> = { '草稿': 'default', '已提交': 'gold', '已开具': 'green' }
    return <Tag color={colors[s]}>{s}</Tag>
  }},
  {
    title: '操作', key: 'actions', render: (_: unknown, record: { status: string }) => (
      <Space>
        <Button type="link" size="small">查看</Button>
        {record.status === '已开具'
          ? <Button type="link" size="small" style={{ color: '#52c41a' }}>导出PDF</Button>
          : <Button type="link" size="small" style={{ color: '#faad14' }}>标记已开具</Button>
        }
      </Space>
    ),
  },
]

const data = [
  { key: '1', room: '302', company: '北京科技有限公司', tax_id: '91110000BJ00001', email: 'fin@test.com', status: '草稿' },
  { key: '2', room: '303', company: '上海贸易有限公司', tax_id: '91310000SH00002', email: 'acc@test.com', status: '已提交' },
  { key: '3', room: '301', company: '广州网络科技有限公司', tax_id: '91440000GZ00003', email: 'tax@test.com', status: '已开具' },
]

export default function InvoiceManagementPage() {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">📄 发票记录管理</h2>
      <Tabs
        items={[
          { key: 'all', label: '全部', children: <Table columns={columns} dataSource={data} pagination={false} /> },
          { key: 'draft', label: '草稿', children: <Table columns={columns} dataSource={data.filter((d) => d.status === '草稿')} pagination={false} /> },
          { key: 'issued', label: '已开具', children: <Table columns={columns} dataSource={data.filter((d) => d.status === '已开具')} pagination={false} /> },
        ]}
      />
    </div>
  )
}
