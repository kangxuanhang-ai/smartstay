import { useEffect, useState } from 'react'
import { Table, Tag, Space, Button, Tabs, Drawer, message } from 'antd'
import jsPDF from 'jspdf'
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
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerRecord, setDrawerRecord] = useState<any>(null)

  const fetchInvoices = async () => {
    setLoading(true)
    try {
      const { data: invoices } = await apiClient.get('/api/admin/invoices')
      setData(invoices.map((inv: InvoiceRow, i: number) => ({ ...inv, key: String(i) })))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchInvoices().catch(() => {}) }, [])

  const handleMarkIssued = async (id: string) => {
    try {
      await apiClient.put(`/api/admin/invoices/${id}/mark-issued`)
      message.success('已标记为已开具')
      fetchInvoices()
    } catch {
      message.error('操作失败')
    }
  }

  const handleExportPDF = (record: any) => {
    const doc = new jsPDF()
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(18)
    doc.text('Invoice / Fapiao', 20, 20)
    doc.setFontSize(12)
    doc.text(`Order ID: ${record.order_id || record.id}`, 20, 40)
    doc.text(`Company: ${record.company_name || '-'}`, 20, 50)
    doc.text(`Tax ID: ${record.tax_id || '-'}`, 20, 60)
    doc.text(`Email: ${record.email || '-'}`, 20, 70)
    doc.text(`Status: ${record.status}`, 20, 80)
    doc.text(`Date: ${new Date().toLocaleDateString()}`, 20, 90)
    doc.save(`invoice-${record.id}.pdf`)
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
      title: '操作', key: 'actions', width: 200,
      render: (_: unknown, record: any) => (
        <Space>
          <Button type="link" size="small" onClick={() => {
            setDrawerRecord(record)
            setDrawerOpen(true)
          }}>查看</Button>
          {record.status === 'issued' && (
            <Button type="link" size="small" style={{ color: '#52c41a' }}
              onClick={() => handleExportPDF(record)}>
              导出PDF
            </Button>
          )}
          {record.status === 'draft' && (
            <Button type="link" size="small"
              onClick={() => handleMarkIssued(record.id)}>
              标记已开具
            </Button>
          )}
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
      <Drawer
        title="发票详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={400}
      >
        {drawerRecord && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div><strong>订单号：</strong>{drawerRecord.order_id || drawerRecord.id}</div>
            <div><strong>公司名称：</strong>{drawerRecord.company_name || '-'}</div>
            <div><strong>税号：</strong>{drawerRecord.tax_id || '-'}</div>
            <div><strong>邮箱：</strong>{drawerRecord.email || '-'}</div>
            <div><strong>地址：</strong>{drawerRecord.address || '-'}</div>
            <div><strong>状态：</strong>{drawerRecord.status === 'issued' ? '已开具' : '草稿'}</div>
          </div>
        )}
      </Drawer>
    </div>
  )
}
