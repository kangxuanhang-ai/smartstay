import { useState, useEffect } from 'react'
import { Card, Button, Select, message, Badge } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'

interface WorkOrder {
  id: string
  room_id: string
  type: string
  content: string
  assigned_resource: string | null
  status: string
  ai_generated: boolean
  created_at: string
}

export default function WorkOrderBoard() {
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [staff, setStaff] = useState('')

  const fetchOrders = () => apiClient.get('/api/work-orders/').then(({ data }) => setOrders(data))

  useEffect(() => { fetchOrders() }, [])

  const pendingOrders = orders.filter((o) => o.status === 'submitted')
  const activeOrders = orders.filter((o) => ['accepted', 'processing'].includes(o.status))
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
      fetchOrders()
    } catch { message.error('操作失败') }
  }

  const handleComplete = async (id: string) => {
    try {
      await apiClient.put(`/api/work-orders/${id}/complete`)
      message.success('已核销完成')
      fetchOrders()
    } catch { message.error('操作失败') }
  }

  const handleAssign = async (id: string) => {
    if (!staff) { message.warning('请先选择指派人员'); return }
    await apiClient.put(`/api/work-orders/${id}/assign`, { assigned_resource: staff })
    message.success('已指派')
    setStaff('')
    fetchOrders()
  }

  const handleComplete = async (id: string) => {
    await apiClient.put(`/api/work-orders/${id}/complete`)
    message.success('已核销完成')
    fetchOrders()
  }

  const OrderCard = ({ wo, showAccept }: { wo: WorkOrder; showAccept?: boolean }) => (
    <Card size="small" className="!mb-4 !shadow-sm !border !border-slate-200 hover:!shadow-md !transition-shadow !duration-200">
      <div className="!flex !items-center !justify-between !mb-3">
        <strong className="!text-sm !text-slate-800 !truncate">
          {wo.type === 'delivery' ? '📦' : '🔧'} {wo.content}
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
        <div className="!flex !flex-wrap !gap-2">
          <Button size="small" type="primary" onClick={() => handleAccept(wo.id)}>接单</Button>
          <Button size="small" onClick={() => handleAssign(wo.id)}>指派处理</Button>
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

      <div className="!mb-6 !flex !flex-wrap !items-center !gap-3">
        <span className="!text-sm !font-medium !text-slate-600">指派人员：</span>
        <Select
          style={{ width: 220 }}
          placeholder="选择值班保洁/维修"
          value={staff || undefined}
          onChange={setStaff}
          allowClear
          options={[
            { value: '张阿姨', label: '🧹 张阿姨 (保洁)' },
            { value: '李师傅', label: '🔧 李师傅 (维修)' },
            { value: '王保洁', label: '🧹 王保洁 (保洁)' },
          ]}
        />
      </div>

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
    </div>
  )
}
