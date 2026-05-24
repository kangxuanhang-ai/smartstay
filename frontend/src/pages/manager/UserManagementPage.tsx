import { useEffect, useState } from 'react'
import { Table, Button, Tag, Space, Tabs } from 'antd'
import apiClient from '../../api/client'

interface UserRow {
  id: string
  id_card: string
  phone: string
  name: string
  role: string
  is_first_login: boolean
  created_at: string
}

export default function UserManagementPage() {
  const [staffData, setStaffData] = useState<UserRow[]>([])
  const [guestData, setGuestData] = useState<UserRow[]>([])
  const [loading, setLoading] = useState(false)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const [{ data: staff }, { data: guests }] = await Promise.all([
        apiClient.get('/api/admin/users?role=front_desk'),
        apiClient.get('/api/admin/users?role=guest'),
      ])
      // Also fetch manager and admin
      const { data: mgr } = await apiClient.get('/api/admin/users?role=manager')
      const { data: adm } = await apiClient.get('/api/admin/users?role=admin')
      setStaffData([...staff, ...mgr, ...adm].map((u: UserRow, i: number) => ({ ...u, key: String(i) })))
      setGuestData(guests.map((u: UserRow, i: number) => ({ ...u, key: String(i) })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name' },
    { title: '身份证号/用户名', dataIndex: 'id_card', key: 'id_card', width: 200 },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 140 },
    { title: '角色', dataIndex: 'role', key: 'role', width: 100, render: (r: string) => <Tag>{r}</Tag> },
    { title: '状态', dataIndex: 'is_first_login', key: 'status', width: 120,
      render: (v: boolean) => <Tag color={v ? 'orange' : 'green'}>{v ? '首次登录' : '正常'}</Tag> },
    {
      title: '操作', key: 'actions', width: 140, render: () => (
        <Space>
          <Button type="link" size="small">编辑</Button>
          <Button type="link" size="small" danger>禁用</Button>
        </Space>
      ),
    },
  ]

  const guestColumns = columns.filter((c) => c.key !== 'actions')

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">👥 用户管理</h2>
        <Button type="primary">+ 创建员工账号</Button>
      </div>
      <Tabs
        items={[
          { key: 'staff', label: `👨‍💼 员工 B端 (${staffData.length})`,
            children: <Table columns={columns} dataSource={staffData} loading={loading} pagination={false} /> },
          { key: 'guest', label: `👤 住客 C端 (${guestData.length})`,
            children: <Table columns={guestColumns} dataSource={guestData} loading={loading} pagination={false} /> },
        ]}
      />
    </div>
  )
}
