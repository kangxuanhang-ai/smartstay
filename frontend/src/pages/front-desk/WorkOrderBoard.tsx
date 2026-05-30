import { useState, useEffect, useRef } from 'react'
import { Card, Button, Select, message, Badge, notification } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'
import { useWebSocket } from '../../hooks/useWebSocket'
import NewWorkOrderAlert from './NewWorkOrderAlert'

interface WorkOrder {
  id: string
  room_id: string
  room_number?: string
  type: string
  content: string
  assigned_resource: string | null
  status: string
  ai_generated: boolean
  created_at: string
}

interface StaffUser {
  id: string
  name: string
  role: string
}

export default function WorkOrderBoard() {
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [staffList, setStaffList] = useState<StaffUser[]>([])
  const [staff, setStaff] = useState('')
  const [alertOpen, setAlertOpen] = useState(false)
  const [newOrder, setNewOrder] = useState<WorkOrder | null>(null)
  const [assigningId, setAssigningId] = useState<string | null>(null)
  const ws = useWebSocket()

  const fetchOrders = () => apiClient.get('/api/work-orders/').then(({ data }) => setOrders(data))

  const fetchStaff = (workOrderType?: string) => {
    const params = workOrderType ? `?work_order_type=${workOrderType}` : ''
    apiClient.get(`/api/work-orders/staff${params}`)
      .then(({ data }) => setStaffList(data))
      .catch(() => {})
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  useEffect(() => {
    const unsubNew = ws.on('work_order.new', (data) => {
      fetchOrders()
      setNewOrder({
        id: data.order_id,
        room_id: data.room_number || '',
        type: data.type,
        content: data.content,
        assigned_resource: null,
        status: 'submitted',
        ai_generated: true,
        created_at: new Date().toISOString(),
      })
      setAlertOpen(true)
      notification.info({
        message: '新工单提醒',
        description: `${data.type === 'delivery' ? '📦' : '🔧'} ${data.content}`,
        placement: 'topRight',
      })
    })

    const unsubStatus = ws.on('work_order.status_change', () => {
      fetchOrders()
    })

    return () => {
      unsubNew()
      unsubStatus()
    }
  }, [ws])

  const pendingOrders = orders.filter((o) => ['submitted', 'accepted'].includes(o.status))
  const activeOrders = orders.filter((o) => o.status === 'processing')
  const completedOrders = orders.filter((o) => o.status === 'completed')

  const handleAccept = async (id: string) => {
    try {
      await apiClient.put(`/api/work-orders/${id}/accept`)
      message.success('已接单')
      fetchOrders()
    } catch { message.error('操作失败') }
  }

  const handleAssign = async (id: string) => {
    if (!staff) { message.warning('请先选择指派人员'); return }
    try {
      await apiClient.put(`/api/work-orders/${id}/assign`, { assigned_resource: staff })
      message.success('已指派')
      setStaff('')
      setAssigningId(null)
      fetchOrders()
    } catch { message.error('操作失败') }
  }

  const startAssign = (id: string, workOrderType: string) => {
    setAssigningId(id)
    setStaff('')
    fetchStaff(workOrderType)
  }

  const handleComplete = async (id: string) => {
    try {
      await apiClient.put(`/api/work-orders/${id}/complete`)
      message.success('已核销完成')
      fetchOrders()
    } catch { message.error('操作失败') }
  }

  const OrderCard = ({ wo, showAccept }: { wo: WorkOrder; showAccept?: boolean }) => (
    <Card size="small" className="!mb-4 !shadow-sm !border !border-slate-200 hover:!shadow-md !transition-shadow !duration-200">
      <div className="!flex !items-center !justify-between !mb-3">
        <strong className="!text-sm !text-slate-800 !truncate">
          {wo.type === 'delivery' ? '📦' : '🔧'} {wo.content}
          {wo.room_number && <span className="!ml-2 !text-xs !font-normal !text-slate-400">Room {wo.room_number}</span>}
        </strong>
        <span className="!text-xs !text-slate-500 !shrink-0 !ml-2">
          {new Date(wo.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      {wo.assigned_resource && (
        <div className="!text-xs !text-slate-600 !mb-3">
          <span className="!text-slate-500">指派：</span>
          <span className="!font-medium">{wo.assigned_resource}</span>
        </div>
      )}
      {showAccept && (
        <div className="!flex !flex-wrap !items-center !gap-2">
          {wo.status === 'submitted' && (
            <Button size="small" type="primary" onClick={() => handleAccept(wo.id)}>接单</Button>
          )}
          {wo.status === 'accepted' && (
            <span className="!inline-flex !items-center !gap-1 !text-xs !text-blue-600 !bg-blue-50 !px-2 !py-0.5 !rounded-full">
              ✅ 已接单
            </span>
          )}
          {assigningId === wo.id ? (
            <div className="!flex !items-center !gap-1">
              <Select
                style={{ width: 130 }}
                size="small"
                placeholder={wo.type === 'delivery' ? '选保洁' : '选维修'}
                value={staff || undefined}
                onChange={setStaff}
                options={staffList.map((s) => ({ value: s.name, label: s.name }))}
              />
              <Button size="small" type="primary" onClick={() => handleAssign(wo.id)}>确认</Button>
              <Button size="small" onClick={() => { setAssigningId(null); setStaff('') }}>取消</Button>
            </div>
          ) : (
            <Button size="small" onClick={() => startAssign(wo.id, wo.type)}>指派处理</Button>
          )}
        </div>
      )}
      {!showAccept && wo.status === 'processing' && (
        <Button size="small" type="primary" danger onClick={() => handleComplete(wo.id)}>确认完成</Button>
      )}
      {!showAccept && wo.status === 'completed' && (
        <span className="!inline-flex !items-center !gap-1 !text-sm !font-semibold !text-green-600 !bg-green-50 !px-3 !py-1 !rounded-full">
          ✅ 已完成
        </span>
      )}
    </Card>
  )

  return (
    <div>
      <h2 className="!text-xl !font-bold !text-slate-800 !mb-6">📋 客服工单流看板</h2>

      <div className="!grid !grid-cols-1 xl:!grid-cols-2 !gap-6">
        <div>
          <div className="!flex !items-center !gap-2 !mb-4">
            <ClockCircleOutlined className="!text-amber-500 !text-lg" />
            <span className="!text-base !font-semibold !text-slate-800">待指派</span>
            <Badge count={pendingOrders.length} color="#f59e0b" />
          </div>
          {pendingOrders.map((wo) => <OrderCard key={wo.id} wo={wo} showAccept />)}
          {pendingOrders.length === 0 && (
            <div className="!text-slate-400 !text-sm !py-8 !text-center !bg-slate-50 !rounded-lg !border !border-dashed !border-slate-200">
              暂无待指派工单
            </div>
          )}
        </div>

        <div>
          <div className="!flex !items-center !gap-2 !mb-4">
            <CheckCircleOutlined className="!text-green-500 !text-lg" />
            <span className="!text-base !font-semibold !text-slate-800">处理中 / 已完成</span>
            <Badge count={activeOrders.length} color="#3b82f6" />
          </div>
          {[...activeOrders, ...completedOrders].map((wo) => <OrderCard key={wo.id} wo={wo} />)}
          {activeOrders.length === 0 && completedOrders.length === 0 && (
            <div className="!text-slate-400 !text-sm !py-8 !text-center !bg-slate-50 !rounded-lg !border !border-dashed !border-slate-200">
              暂无工单
            </div>
          )}
        </div>
      </div>

      <NewWorkOrderAlert
        open={alertOpen}
        workOrder={newOrder}
        onClose={() => setAlertOpen(false)}
        onAccept={() => { setAlertOpen(false); fetchOrders() }}
      />
    </div>
  )
}
