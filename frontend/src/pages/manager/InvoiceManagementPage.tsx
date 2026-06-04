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

  useEffect(() => { fetchInvoices().catch(() => message.error('获取发票列表失败')) }, [])

  const handleMarkIssued = async (id: string) => {
    try {
      await apiClient.put(`/api/admin/invoices/${id}/mark-issued`)
      message.success('已标记为已开具')
      fetchInvoices()
    } catch {
      message.error('操作失败')
    }
  }

  const handleExportPDF = async (record: any) => {
    const orderId = record.order_id || record.id
    let bill: any = null
    try {
      const { data } = await apiClient.get(`/api/orders/${orderId}/bill`)
      bill = data
    } catch {
      // fallback: generate without bill data
    }

    const doc = new jsPDF()
    const pageW = 210
    const margin = 20
    let y = 20

    // ?? Header: Hotel Info ??
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(20)
    doc.setTextColor(37, 99, 235)
    doc.text('SmartStay Hotel', margin, y)
    y += 8
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)
    doc.setTextColor(100, 100, 100)
    doc.text('Beijing CBD, SOHO Modern City, No.88 Jianguo Road, Chaoyang District', margin, y)
    y += 5
    doc.text('Tel: 138-0000-0002  |  www.smartstay.com', margin, y)
    y += 10

    // ?? Divider line ??
    doc.setDrawColor(37, 99, 235)
    doc.setLineWidth(0.8)
    doc.line(margin, y, pageW - margin, y)
    y += 10

    // ?? Invoice Title ??
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(16)
    doc.setTextColor(30, 30, 30)
    doc.text('INVOICE', margin, y)
    y += 8

    // ?? Invoice meta (right aligned) ??
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)
    doc.setTextColor(80, 80, 80)
    const invoiceNo = `INV-${orderId.substring(0, 8).toUpperCase()}`
    const issueDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    doc.text(`Invoice No: ${invoiceNo}`, pageW - margin - 60, y - 8)
    doc.text(`Date: ${issueDate}`, pageW - margin - 60, y - 3)
    doc.text(`Status: ${record.status === 'issued' ? 'ISSUED' : 'DRAFT'}`, pageW - margin - 60, y + 2)
    y += 10

    // ?? Bill To section ??
    doc.setFillColor(245, 245, 250)
    doc.roundedRect(margin, y, pageW - 2 * margin, 28, 2, 2, 'F')
    y += 6
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(8)
    doc.setTextColor(100, 100, 100)
    doc.text('BILL TO', margin + 4, y)
    y += 5
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    doc.setTextColor(30, 30, 30)
    doc.text(record.company_name || '-', margin + 4, y)
    y += 5
    doc.setFontSize(9)
    doc.setTextColor(80, 80, 80)
    doc.text(`Tax ID: ${record.tax_id || '-'}`, margin + 4, y)
    doc.text(`Email: ${record.email || '-'}`, margin + 80, y)
    y += 15

    // ?? Items Table ??
    doc.setFillColor(37, 99, 235)
    doc.rect(margin, y, pageW - 2 * margin, 8, 'F')
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(9)
    doc.setTextColor(255, 255, 255)
    doc.text('Description', margin + 4, y + 5.5)
    doc.text('Qty', pageW - margin - 40, y + 5.5)
    doc.text('Amount', pageW - margin - 2, y + 5.5, { align: 'right' })
    y += 8

    doc.setTextColor(30, 30, 30)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)

    const formatFen = (fen: number) => `\u00a5${(fen / 100).toFixed(2)}`

    // Room rate row
    const nights = bill?.nights || 1
    const dailyRate = bill?.daily_rate || bill?.room_rate || 0
    const roomDesc = nights > 1
      ? `Room Charge (${nights} nights @ ${formatFen(dailyRate)}/night)`
      : 'Room Charge (1 night)'
    doc.text(roomDesc, margin + 4, y + 5)
    doc.text(String(nights), pageW - margin - 35, y + 5)
    doc.text(formatFen(bill?.room_rate || dailyRate), pageW - margin - 2, y + 5, { align: 'right' })
    y += 7
    doc.setDrawColor(220, 220, 220)
    doc.line(margin + 4, y, pageW - margin - 4, y)
    y += 1

    // Consumption rows
    const consumptions = bill?.consumptions || []
    for (const c of consumptions) {
      doc.text(c.item_name || '-', margin + 4, y + 5)
      doc.text(String(c.quantity || 1), pageW - margin - 35, y + 5)
      doc.text(formatFen((c.amount || 0) * (c.quantity || 1)), pageW - margin - 2, y + 5, { align: 'right' })
      y += 7
      doc.line(margin + 4, y, pageW - margin - 4, y)
      y += 1
    }

    // ?? Totals ??
    y += 4
    const consumptionTotal = bill?.consumption_total || 0
    const grandTotal = bill?.grand_total || 0

    doc.setFont('helvetica', 'normal')
    doc.text('Room Subtotal:', margin + 80, y + 5)
    doc.text(formatFen(bill?.room_rate || dailyRate), pageW - margin - 2, y + 5, { align: 'right' })
    y += 7
    doc.text('Consumption Subtotal:', margin + 80, y + 5)
    doc.text(formatFen(consumptionTotal), pageW - margin - 2, y + 5, { align: 'right' })
    y += 9

    // Grand total with highlight
    doc.setFillColor(37, 99, 235)
    doc.roundedRect(margin, y - 2, pageW - 2 * margin, 10, 2, 2, 'F')
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(11)
    doc.setTextColor(255, 255, 255)
    doc.text('TOTAL', margin + 4, y + 5)
    doc.text(formatFen(grandTotal), pageW - margin - 2, y + 5, { align: 'right' })
    y += 18

    // ?? Footer ??
    doc.setDrawColor(200, 200, 200)
    doc.line(margin, y, pageW - margin, y)
    y += 6
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(140, 140, 140)
    doc.text('This is a computer-generated invoice. For questions, contact front desk or email support@smartstay.com', margin, y)
    y += 4
    doc.text('SmartStay Hotel  |  Beijing CBD  |  Tel: 138-0000-0002', margin, y)

    doc.save(`invoice-${invoiceNo}.pdf`)
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
