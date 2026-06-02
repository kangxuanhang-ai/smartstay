import { useEffect, useState } from 'react'
import { Table, Button, Tag, Space, Tabs, Modal, Form, Input, Select, message } from 'antd'
import apiClient from '../../api/client'

interface UserRow {
  id: string
  id_card: string
  phone: string
  name: string
  role: string
  is_first_login: boolean
  is_active: boolean
  created_at: string
}

export default function UserManagementPage() {
  const [staffData, setStaffData] = useState<UserRow[]>([])
  const [guestData, setGuestData] = useState<UserRow[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<any>(null)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const [{ data: staff }, { data: guests }] = await Promise.all([
        apiClient.get('/api/admin/users?role=front_desk'),
        apiClient.get('/api/admin/users?type=guest'),
      ])
      const { data: mgr } = await apiClient.get('/api/admin/users?role=manager')
      const { data: adm } = await apiClient.get('/api/admin/users?role=admin')
      setStaffData([...staff, ...mgr, ...adm].map((u: UserRow, i: number) => ({ ...u, key: String(i) })))
      setGuestData(guests.map((u: UserRow, i: number) => ({ ...u, key: String(i) })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers().catch(() => {}) }, [])

  const handleCreateUser = async () => {
    const values = await form.validateFields()
    try {
      await apiClient.post('/api/admin/users', values)
      message.success('员工账号创建成功')
      form.resetFields()
      setCreateOpen(false)
      fetchUsers()
    } catch {
      message.error('创建失败')
    }
  }

  const handleEditUser = async () => {
    try {
      const values = await editForm.validateFields()
      await apiClient.put(`/api/admin/users/${editRecord.id}`, values)
      message.success('更新成功')
      setEditOpen(false)
      editForm.resetFields()
      fetchUsers()
    } catch {
      message.error('更新失败')
    }
  }

  const handleToggleStatus = async (record: any) => {
    const action = record.is_active === false ? '启用' : '禁用'
    Modal.confirm({
      title: `确认${action}`,
      content: `确定要${action}该员工吗？`,
      onOk: async () => {
        try {
          await apiClient.put(`/api/admin/users/${record.id}/toggle-status`)
          message.success(`已${action}`)
          fetchUsers()
        } catch {
          message.error(`${action}失败`)
        }
      },
    })
  }

  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name' },
    { title: '用户名', dataIndex: 'id_card', key: 'id_card', width: 140 },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 140 },
    { title: '角色', dataIndex: 'role', key: 'role', width: 110, render: (r: string) => <Tag>{r}</Tag> },
    { title: '状态', dataIndex: 'is_first_login', key: 'status', width: 120,
      render: (_: boolean, record: any) => {
        if (record.is_active === false) return <Tag color="red">已禁用</Tag>
        return record.is_first_login ? <Tag color="orange">首次登录</Tag> : <Tag color="green">正常</Tag>
      },
    },
    { title: '操作', key: 'actions', width: 140, render: (_: unknown, record: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => {
            setEditRecord(record)
            editForm.setFieldsValue({ name: record.name, phone: record.phone, role: record.role })
            setEditOpen(true)
          }}>编辑</Button>
          <Button type="link" size="small" danger={record.is_active !== false}
            onClick={() => handleToggleStatus(record)}>
            {record.is_active === false ? '启用' : '禁用'}
          </Button>
        </Space>
      ),
    },
  ]

  const guestColumns = columns.filter((c) => c.key !== 'actions')

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">👥 用户管理</h2>
        <Button type="primary" onClick={() => setCreateOpen(true)}>+ 创建员工账号</Button>
      </div>
      <Tabs
        items={[
          { key: 'staff', label: `👨‍💼 员工 B端 (${staffData.length})`,
            children: <Table columns={columns} dataSource={staffData} loading={loading} pagination={false} /> },
          { key: 'guest', label: `👤 住客 C端 (${guestData.length})`,
            children: <Table columns={guestColumns} dataSource={guestData} loading={loading} pagination={false} /> },
        ]}
      />
      <Modal
        title="创建员工账号"
        open={createOpen}
        onOk={handleCreateUser}
        onCancel={() => { form.resetFields(); setCreateOpen(false) }}
        okText="确认创建"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input placeholder="请输入员工姓名" />
          </Form.Item>
          <Form.Item name="id_card" label="用户名（岗位拼音）" rules={[{ required: true }]}>
            <Input placeholder="如：qiantai、manager" />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="front_desk">
            <Select options={[
              { value: 'front_desk', label: '前台接待' },
              { value: 'manager', label: '总店长' },
              { value: 'admin', label: '系统管理员' },
            ]} />
          </Form.Item>
        </Form>
        <p className="text-xs text-gray-400">初始密码：123456 · 首次登录需改密</p>
      </Modal>
      <Modal
        title="编辑员工"
        open={editOpen}
        onOk={handleEditUser}
        onCancel={() => { setEditOpen(false); editForm.resetFields() }}
        okText="确认更新"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={[
              { value: 'front_desk', label: '前台接待' },
              { value: 'manager', label: '总店长' },
              { value: 'admin', label: '系统管理员' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
