import { useEffect, useState } from 'react'
import { Table, Tag, Space, Button, Tabs, message } from 'antd'
import apiClient from '../../api/client'

interface InvoiceRow {
  id: string
  order_id: string
  company_name: string
  tax_id: string
  email: string
  status: string
  created_at: string
}

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  submitted: { color: 'gold', label: '已提交' },
  issued: { color: 'green', label: '已开具' },
}

export default function InvoiceManagementPage() {
  const [data, setData] = useState<InvoiceRow[]>([])
  const [loading, setLoading] = useState(false)

  const fetchInvoices = async () => {
    setLoading(true)
    try {
      const { data: invoices } = await apiClient.get('/api/admin/invoices')
      setData(invoices.map((inv: InvoiceRow, i: number) => ({ ...inv, key: String(i) })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchInvoices() }, [])

  const handleMarkIssued = async (id: string) => {
    try {
      await apiClient.put(`/api/admin/invoices/${id}/mark-issued`)
      message.success('已标记为已开具')
      fetchInvoices()
    } catch {
      message.error('操作失败')
    }
  }

  const getRoomLabel = (orderId: string) => orderId.substring(0, 8) + '...'

  const columns = [
    { title: '房间', dataIndex: 'order_id', key: 'room', width: 120, render: (id: string) => getRoomLabel(id) },
    { title: '公司抬头', dataIndex: 'company_name', key: 'company' },
    { title: '税号', dataIndex: 'tax_id', key: 'tax_id', width: 180 },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={STATUS_TAG[s]?.color}>{STATUS_TAG[s]?.label || s}</Tag> },
    {
      title: '操作', key: 'actions', width: 160, render: (_: unknown, record: InvoiceRow) => (
        <Space>
          <Button type="link" size="small">查看</Button>
          {record.status === 'issued'
            ? <Button type="link" size="small" style={{ color: '#52c41a' }}>导出PDF</Button>
            : <Button type="link" size="small" style={{ color: '#faad14' }} onClick={() => handleMarkIssued(record.id)}>标记已开具</Button>
          }
        </Space>
      ),
    },
  ]

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">📄 发票记录管理</h2>
      <Tabs
        items={[
          { key: 'all', label: `全部 (${data.length})`,
            children: <Table columns={columns} dataSource={data} loading={loading} pagination={false} /> },
          { key: 'draft', label: `草稿 (${data.filter((d) => d.status === 'draft').length})`,
            children: <Table columns={columns} dataSource={data.filter((d) => d.status === 'draft')} loading={loading} pagination={false} /> },
          { key: 'issued', label: `已开具 (${data.filter((d) => d.status === 'issued').length})`,
            children: <Table columns={columns} dataSource={data.filter((d) => d.status === 'issued')} loading={loading} pagination={false} /> },
        ]}
      />
    </div>
  )
}
