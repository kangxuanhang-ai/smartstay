import { useState, useEffect } from 'react'
import { Card, Tag, Dropdown, Modal, Descriptions, Table, Timeline, Button, Spin, Empty, message } from 'antd'
import { HomeOutlined, ClockCircleOutlined, DollarOutlined, ToolOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'
import { useWebSocket } from '../../hooks/useWebSocket'
import CheckInModal from './CheckInModal'

interface Room {
  id: string
  room_number: string
  room_type: string
  status: string
  floor: number
  current_price: number
}

const STATUS_COLORS: Record<string, string> = {
  vacant: '#22c55e',
  occupied: '#ef4444',
  dirty: '#f59e0b',
  maintenance: '#6b7280',
}

const STATUS_LABELS: Record<string, string> = {
  vacant: '空房',
  occupied: '有人住',
  dirty: '脏房',
  maintenance: '维修中',
}

const ROOM_TYPE_LABELS: Record<string, string> = {
  big_bed: '大床房',
  twin: '双床房',
  suite: '套房',
}

const SOURCE_LABELS: Record<string, string> = {
  self_app: '自助App',
  front_desk: '前台',
  ctrip: '携程',
  meituan: '美团',
}

const WORK_ORDER_STATUS: Record<string, { color: string; label: string }> = {
  submitted: { color: 'blue', label: '已提交' },
  accepted: { color: 'orange', label: '已接单' },
  processing: { color: 'processing', label: '处理中' },
  completed: { color: 'green', label: '已完成' },
}

interface ActiveOrder {
  id: string
  room_id: string
  user_id: string
  status: string
  source: string
  check_in_time: string | null
  guest_name: string | null
  guest_id_card: string | null
  guest_phone: string | null
}

interface BillingLine {
  item_name: string
  category: string
  amount: number
  quantity: number
  consumed_at: string
}

interface BillData {
  order_id: string
  room_rate: number
  consumptions: BillingLine[]
  consumption_total: number
  grand_total: number
}

interface WorkOrder {
  id: string
  room_id: string
  type: string
  content: string
  assigned_resource: string | null
  status: string
  ai_generated: boolean
  created_at: string | null
}

interface RoomDetailModalProps {
  room: Room
  open: boolean
  onClose: () => void
  onCheckout: (roomId: string) => void
}

function RoomDetailModal({ room, open, onClose, onCheckout }: RoomDetailModalProps) {
  const [loading, setLoading] = useState(false)
  const [order, setOrder] = useState<ActiveOrder | null>(null)
  const [bill, setBill] = useState<BillData | null>(null)
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([])

  useEffect(() => {
    if (!open || room.status !== 'occupied') return
    setLoading(true)
    Promise.all([
      apiClient.get(`/api/orders/room/${room.id}/active`).catch(() => null),
      apiClient.get('/api/work-orders/').catch(() => ({ data: [] })),
    ]).then(([orderRes, woRes]) => {
      const activeOrder = orderRes?.data
      setOrder(activeOrder)
      setWorkOrders(
        (woRes?.data || []).filter((wo: WorkOrder) => wo.room_id === room.id)
      )
      if (activeOrder?.id) {
        return apiClient.get(`/api/orders/${activeOrder.id}/bill`).catch(() => null)
      }
      return null
    }).then((billRes) => {
      if (billRes?.data) setBill(billRes.data)
    }).finally(() => setLoading(false))
  }, [open, room.id, room.status])

  const handleCheckout = () => {
    onClose()
    onCheckout(room.id)
  }

  return (
    <Modal
      title={
        <span>
          房间 {room.room_number} · {ROOM_TYPE_LABELS[room.room_type] || room.room_type} · {room.floor}楼
        </span>
      }
      open={open}
      onCancel={onClose}
      width={640}
      footer={
        <div className="!flex !justify-end !gap-2">
          <Button onClick={onClose}>关闭</Button>
          <Button danger type="primary" disabled={!order} onClick={handleCheckout}>办理退房</Button>
        </div>
      }
    >
      {loading ? (
        <div className="!flex !justify-center !py-10"><Spin /></div>
      ) : (
        <div className="!flex !flex-col !gap-5">
          {/* 入住信息 */}
          <div>
            <h4 className="!mb-2 !text-slate-700"><ClockCircleOutlined className="!mr-1" />入住信息</h4>
            {order ? (
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="入住时间">
                  {order.check_in_time ? new Date(order.check_in_time).toLocaleString('zh-CN') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="来源">{SOURCE_LABELS[order.source || ''] || order.source || '-'}</Descriptions.Item>
                <Descriptions.Item label="当前房价">¥{Math.round(room.current_price / 100)}/晚</Descriptions.Item>
                <Descriptions.Item label="房间状态">
                  <Tag color={STATUS_COLORS[room.status]}>{STATUS_LABELS[room.status]}</Tag>
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <div className="!bg-amber-50 !border !border-amber-200 !rounded !p-3 !text-sm !text-amber-700">
                该房间未通过正规入住流程办理，无订单记录。请通过右键菜单"快捷开房"重新办理入住。
              </div>
            )}
          </div>

          {/* 住客信息 */}
          {order && (order.guest_name || order.guest_id_card || order.guest_phone) && (
            <div>
              <h4 className="!mb-2 !text-slate-700">👤 住客信息</h4>
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="姓名">{order.guest_name || '-'}</Descriptions.Item>
                <Descriptions.Item label="手机号">{order.guest_phone || '-'}</Descriptions.Item>
                <Descriptions.Item label="身份证号" span={2}>{order.guest_id_card || '-'}</Descriptions.Item>
              </Descriptions>
            </div>
          )}

          {/* 账单明细 */}
          <div>
            <h4 className="!mb-2 !text-slate-700"><DollarOutlined className="!mr-1" />账单明细</h4>
            {bill ? (
              <>
                <Table
                  size="small"
                  dataSource={bill.consumptions}
                  rowKey={(r) => r.item_name + r.consumed_at}
                  pagination={false}
                  columns={[
                    { title: '项目', dataIndex: 'item_name', key: 'item_name' },
                    { title: '单价', dataIndex: 'amount', key: 'amount', render: (v: number) => `¥${v / 100}` },
                    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
                    { title: '小计', key: 'subtotal', render: (_, r) => `¥${(r.amount * r.quantity) / 100}` },
                  ]}
                />
                <div className="!mt-2 !text-right !text-sm !text-slate-600">
                  <span>房费: ¥{bill.room_rate / 100}</span>
                  <span className="!mx-3">|</span>
                  <span>消费合计: ¥{bill.consumption_total / 100}</span>
                  <span className="!mx-3">|</span>
                  <span className="!font-bold !text-blue-600">总计: ¥{bill.grand_total / 100}</span>
                </div>
              </>
            ) : (
              <Empty description="暂无消费记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </div>

          {/* 服务工单 */}
          <div>
            <h4 className="!mb-2 !text-slate-700"><ToolOutlined className="!mr-1" />服务工单</h4>
            {workOrders.length > 0 ? (
              <Timeline
                items={workOrders.map((wo) => ({
                  color: WORK_ORDER_STATUS[wo.status]?.color || 'gray',
                  content: (
                    <div>
                      <span className="!font-medium">{wo.type}</span>
                      <span className="!mx-2 !text-slate-400">·</span>
                      <span className="!text-xs !text-slate-500">{WORK_ORDER_STATUS[wo.status]?.label || wo.status}</span>
                      {wo.ai_generated && <Tag color="purple" className="!ml-1 !text-xs">AI生成</Tag>}
                      {wo.assigned_resource && <span className="!ml-2 !text-xs !text-slate-500">→ {wo.assigned_resource}</span>}
                      <div className="!text-xs !text-slate-400">{wo.content}</div>
                      {wo.created_at && <div className="!text-xs !text-slate-400">{new Date(wo.created_at).toLocaleString('zh-CN')}</div>}
                    </div>
                  ),
                }))}
              />
            ) : (
              <Empty description="暂无工单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}

export default function RoomGridPage() {
  const [rooms, setRooms] = useState<Room[]>([])
  const [checkInRoom, setCheckInRoom] = useState<string | null>(null)
  const [detailRoom, setDetailRoom] = useState<Room | null>(null)
  const [infoModalOpen, setInfoModalOpen] = useState(false)
  const [infoRoom, setInfoRoom] = useState<Room | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [settleOpen, setSettleOpen] = useState(false)
  const [settleRoom, setSettleRoom] = useState<Room | null>(null)
  const [settleOrder, setSettleOrder] = useState<any>(null)
  const [settleBill, setSettleBill] = useState<any>(null)
  const [settleLoading, setSettleLoading] = useState(false)
  const [paying, setPaying] = useState(false)
  const ws = useWebSocket()

  useEffect(() => {
    apiClient.get('/api/rooms/').then(({ data }) => setRooms(data)).catch(() => message.error('加载房间数据失败'))
  }, [refreshKey])

  useEffect(() => {
    const unsubRoom = ws.on('room.status_change', () => {
      setRefreshKey((k) => k + 1)
    })
    const unsubPay = ws.on('payment.success', () => {
      if (paying) {
        setPaying(false)
        setSettleOpen(false)
        message.success('支付成功，退房完成')
        setRefreshKey((k) => k + 1)
      }
    })
    return () => { unsubRoom(); unsubPay() }
  }, [ws, paying])

  // When user returns from Alipay tab, verify payment status
  useEffect(() => {
    if (!paying) return
    const handleFocus = async () => {
      if (!paying || !settleOrder) return
      try {
        const { data } = await apiClient.post(`/api/orders/${settleOrder.id}/verify-alipay-payment`)
        if (data.paid) {
          setPaying(false)
          setSettleOpen(false)
          message.success('支付成功，退房完成')
          setRefreshKey((k: number) => k + 1)
        } else {
          message.info('支付尚未完成，请在支付宝完成支付后点击确认按钮')
        }
      } catch { /* ignore */ }
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [paying, settleOrder, settleRoom])

  const handleStatusChange = async (roomId: string, status: string) => {
    try {
      await apiClient.put(`/api/rooms/${roomId}/status`, { status })
      message.success('房间状态已更新')
      setRefreshKey((k) => k + 1)
    } catch {
      message.error('操作失败')
    }
  }

  const openSettlement = async (room: Room) => {
    try {
      const { data: order } = await apiClient.get(`/api/orders/room/${room.id}/active`)
      const { data: bill } = await apiClient.get(`/api/orders/${order.id}/bill`)
      setSettleRoom(room)
      setSettleOrder(order)
      setSettleBill(bill)
      setSettleOpen(true)
    } catch {
      message.error('获取账单失败')
    }
  }

  const stats = {
    vacant: rooms.filter((r) => r.status === 'vacant').length,
    occupied: rooms.filter((r) => r.status === 'occupied').length,
    dirty: rooms.filter((r) => r.status === 'dirty').length,
    maintenance: rooms.filter((r) => r.status === 'maintenance').length,
  }

  return (
    <div>
      <div className="!flex !flex-wrap !justify-between !items-center !gap-3 !mb-6">
        <h2 className="!text-xl !font-bold !text-slate-800">📊 实时房态全景</h2>
        <div className="!flex !flex-wrap !gap-2">
          {Object.entries(stats).map(([key, value]) => (
            <Card size="small" key={key}
              styles={{ body: { padding: '8px 16px' } }}
              className="!shadow-sm !border !border-slate-200"
            >
              <span className="!text-lg !font-bold" style={{ color: STATUS_COLORS[key] }}>{value}</span>
              <span className="!text-xs !text-slate-500 !ml-2">{STATUS_LABELS[key]}</span>
            </Card>
          ))}
        </div>
      </div>

      <div className="!grid !grid-cols-1 sm:!grid-cols-2 md:!grid-cols-3 lg:!grid-cols-4 xl:!grid-cols-5 !gap-4">
        {rooms.map((room) => (
          <Dropdown
            key={room.id}
            trigger={['contextMenu']}
            menu={{
              items: [
                // vacant: 快捷开房、设为脏房、设为维修中
                ...(room.status === 'vacant'
                  ? [
                      { key: 'checkin', label: '🚪 快捷开房', onClick: () => setCheckInRoom(room.id) },
                      { key: 'dirty', label: '🧹 设为脏房', onClick: () => handleStatusChange(room.id, 'dirty') },
                      { key: 'lock', label: '🔒 设为维修中', onClick: () => handleStatusChange(room.id, 'maintenance') },
                    ]
                  : []),
                // occupied: 仅办理退房（退房后自动变dirty）
                ...(room.status === 'occupied'
                  ? [{ key: 'checkout', label: '🏃 办理退房', onClick: () => openSettlement(room) }]
                  : []),
                // dirty: 设为空房（保洁完成）、设为维修中
                ...(room.status === 'dirty'
                  ? [
                      { key: 'unlock', label: '🟢 设为空房', onClick: () => handleStatusChange(room.id, 'vacant') },
                      { key: 'lock', label: '🔒 设为维修中', onClick: () => handleStatusChange(room.id, 'maintenance') },
                    ]
                  : []),
                // maintenance: 设为空房（维修完成）
                ...(room.status === 'maintenance'
                  ? [{ key: 'unlock', label: '🟢 设为空房', onClick: () => handleStatusChange(room.id, 'vacant') }]
                  : []),
              ],
            }}
          >
            <Card
              size="small"
              hoverable
              className="!shadow-sm !border-2 !border-slate-200 hover:!shadow-md hover:!border-slate-300 !transition-all !duration-200"
              style={{ borderColor: STATUS_COLORS[room.status] || '#d9d9d9' }}
              styles={{ body: { padding: '16px 12px', textAlign: 'center' } }}
              onClick={() => {
                if (room.status === 'occupied') {
                  setDetailRoom(room)
                } else {
                  setInfoRoom(room)
                  setInfoModalOpen(true)
                }
              }}
            >
              <div className="!flex !items-center !justify-center !gap-1.5 !mb-2 !truncate">
                <HomeOutlined style={{ color: STATUS_COLORS[room.status], fontSize: 16, flexShrink: 0 }} />
                <strong className="!text-xl !font-bold !text-slate-800 !truncate">{room.room_number}</strong>
              </div>
              <div className="!text-xs !text-slate-500 !mb-2">{ROOM_TYPE_LABELS[room.room_type] || room.room_type}</div>
              <Tag color={STATUS_COLORS[room.status]}>{STATUS_LABELS[room.status]}</Tag>
              <div className="!text-base !font-bold !text-blue-600 !mt-2">
                ¥{Math.round(room.current_price / 100)}
              </div>
            </Card>
          </Dropdown>
        ))}
      </div>

      {checkInRoom && (
        <CheckInModal
          roomId={checkInRoom}
          open={!!checkInRoom}
          onClose={() => {
            setCheckInRoom(null)
            setRefreshKey((k) => k + 1)
          }}
        />
      )}

      {detailRoom && (
        <RoomDetailModal
          room={detailRoom}
          open={!!detailRoom}
          onClose={() => setDetailRoom(null)}
          onCheckout={(roomId) => {
            const room = rooms.find((r: Room) => r.id === roomId)
            if (room) openSettlement(room)
          }}
        />
      )}

      <Modal
        title="房间信息"
        open={infoModalOpen}
        onCancel={() => setInfoModalOpen(false)}
        footer={[
          infoRoom?.status === 'vacant' && (
            <Button key="checkin" type="primary" onClick={() => {
              setInfoModalOpen(false)
              setCheckInRoom(infoRoom.id)
            }}>
              快捷开房
            </Button>
          ),
          <Button key="close" onClick={() => setInfoModalOpen(false)}>关闭</Button>,
        ].filter(Boolean)}
      >
        {infoRoom && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div><strong>房间号：</strong>{infoRoom.room_number}</div>
            <div><strong>房型：</strong>{ROOM_TYPE_LABELS[infoRoom.room_type] || infoRoom.room_type}</div>
            <div><strong>状态：</strong>
              <Tag color={STATUS_COLORS[infoRoom.status]}>
                {STATUS_LABELS[infoRoom.status]}
              </Tag>
            </div>
            <div><strong>价格：</strong>¥{(infoRoom.current_price / 100).toFixed(2)}/晚</div>
          </div>
        )}
      </Modal>

      <Modal
        title={paying ? '等待支付' : '退房结算'}
        open={settleOpen}
        onCancel={() => { setSettleOpen(false); setPaying(false) }}
        footer={null}
        width={480}
      >
        {settleRoom && settleOrder && settleBill && (
          paying ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>⏳</div>
              <div style={{ fontSize: 16, marginBottom: 8 }}>请在支付宝完成支付</div>
              <div style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 24 }}>
                ¥{(settleBill.grand_total / 100).toFixed(2)}
              </div>
              <Button
                type="primary"
                block
                style={{ marginBottom: 12 }}
                onClick={async () => {
                  try {
                    const { data } = await apiClient.post(`/api/orders/${settleOrder.id}/verify-alipay-payment`)
                    if (data.paid) {
                      setPaying(false)
                      setSettleOpen(false)
                      message.success('支付成功，退房完成')
                      setRefreshKey((k: number) => k + 1)
                    } else {
                      message.warning('支付尚未完成，请在支付宝完成支付后重试')
                    }
                  } catch (e: any) {
                    message.error(e?.response?.data?.detail || '验证失败，请重试')
                  }
                }}
              >
                已完成支付？点击确认
              </Button>
              <div>
                <Button type="link" onClick={() => setPaying(false)}>返回</Button>
              </div>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: 16 }}>
                <div><strong>房间：</strong>{settleRoom.room_number} {ROOM_TYPE_LABELS[settleRoom.room_type] || settleRoom.room_type}</div>
                <div><strong>住客：</strong>{settleOrder.guest_name || '-'}</div>
              </div>
              <table style={{ width: '100%', marginBottom: 16, borderCollapse: 'collapse' }}>
                <tbody>
                  <tr>
                    <td style={{ padding: '8px 0' }}>房费</td>
                    <td style={{ textAlign: 'right', padding: '8px 0' }}>{'¥'}{(settleBill.room_rate / 100).toFixed(2)}</td>
                  </tr>
                  {settleBill.consumptions?.map((c: any, i: number) => (
                    <tr key={i}>
                      <td style={{ padding: '4px 0', color: '#999' }}>{c.item_name}</td>
                      <td style={{ textAlign: 'right', padding: '4px 0', color: '#999' }}>{'¥'}{(c.amount / 100).toFixed(2)}</td>
                    </tr>
                  ))}
                  <tr style={{ borderTop: '1px solid #333' }}>
                    <td style={{ padding: '8px 0', fontWeight: 'bold' }}>合计</td>
                    <td style={{ textAlign: 'right', padding: '8px 0', fontWeight: 'bold' }}>{'¥'}{(settleBill.grand_total / 100).toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
              <div style={{ display: 'flex', gap: 12 }}>
                <Button
                  style={{ flex: 1 }}
                  disabled={!['ctrip', 'meituan'].includes(settleOrder.source)}
                  loading={settleLoading}
                  onClick={async () => {
                    setSettleLoading(true)
                    await new Promise((r) => setTimeout(r, 2000))
                    try {
                      await apiClient.put(`/api/orders/${settleOrder.id}/checkout`)
                      message.success('退房成功')
                      setSettleOpen(false)
                      setRefreshKey((k: number) => k + 1)
                    } catch {
                      message.error('退房失败')
                    } finally {
                      setSettleLoading(false)
                    }
                  }}
                >
                  线上支付{['ctrip', 'meituan'].includes(settleOrder.source) ? '' : ' (仅携程/美团)'}
                </Button>
                <Button
                  type="primary"
                  style={{ flex: 1 }}
                  onClick={async () => {
                    try {
                      const { data } = await apiClient.post(`/api/orders/${settleOrder.id}/create-alipay-order`)
                      window.open(data.pay_url, '_blank')
                      setPaying(true)
                    } catch {
                      message.error('创建支付订单失败')
                    }
                  }}
                >
                  立即支付 (线下)
                </Button>
              </div>
            </div>
          )
        )}
      </Modal>
    </div>
  )
}
