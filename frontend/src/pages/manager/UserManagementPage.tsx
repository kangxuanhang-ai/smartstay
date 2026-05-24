import { Table, Button, Tag, Space, Tabs } from 'antd'

const columns = [
  { title: '姓名', dataIndex: 'name', key: 'name' },
  { title: '身份证号', dataIndex: 'id_card', key: 'id_card' },
  { title: '手机号', dataIndex: 'phone', key: 'phone' },
  { title: '角色', dataIndex: 'role', key: 'role', render: (r: string) => <Tag>{r}</Tag> },
  { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === '正常' ? 'green' : 'red'}>{s}</Tag> },
  {
    title: '操作', key: 'actions', render: () => (
      <Space>
        <Button type="link" size="small">编辑</Button>
        <Button type="link" size="small" danger>禁用</Button>
      </Space>
    ),
  },
]

const staffData = [
  { key: '1', name: '前台张', id_card: '100...002', phone: '138...002', role: 'front_desk', status: '✅ 正常' },
  { key: '2', name: '总店长', id_card: '100...001', phone: '138...001', role: 'manager', status: '✅ 正常' },
  { key: '3', name: '管理员', id_card: '100...003', phone: '138...003', role: 'admin', status: '✅ 正常' },
]

export default function UserManagementPage() {
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">👥 用户管理</h2>
        <Button type="primary">+ 创建员工账号</Button>
      </div>
      <Tabs
        items={[
          { key: 'staff', label: '👨‍💼 员工 B端', children: <Table columns={columns} dataSource={staffData} pagination={false} /> },
          { key: 'guest', label: '👤 住客 C端 (只读)', children: <div className="text-gray-400 text-sm py-4">住客数据由前台开房自动创建...</div> },
        ]}
      />
    </div>
  )
}
