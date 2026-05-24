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
    await apiClient.put(`/api/work-orders/${id}/accept`)
    message.success('已接单')
    fetchOrders()
  }

  const handleAssign = async (id: string) => {
    if (!staff) { message.warning('请先输入指派人员'); return }
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

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">📋 客服工单流看板</h2>

      <div className="mb-4 flex items-center gap-3">
        <span className="text-sm text-gray-500">指派人员：</span>
        <Select
          style={{ width: 200 }}
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

      <div className="grid grid-cols-2 gap-4">
        {/* Left: Pending */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <ClockCircleOutlined className="text-yellow-500" />
            <span className="font-semibold">待指派</span>
            <Badge count={pendingOrders.length} color="#faad14" />
          </div>
          {pendingOrders.map((wo: WorkOrder) => (
            <Card key={wo.id} size="small" className="mb-3">
              <div className="flex items-center justify-between mb-2">
                <strong>
                  {wo.type === 'delivery' ? '📦' : '🔧'} {wo.content}
                </strong>
                <span className="text-xs text-gray-400">
                  {new Date(wo.created_at).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex gap-2">
                <Button size="small" type="primary" onClick={() => handleAccept(wo.id)}>接单</Button>
                <Button size="small" onClick={() => handleAssign(wo.id)}>直接指派</Button>
              </div>
            </Card>
          ))}
          {pendingOrders.length === 0 && <div className="text-gray-400 text-sm py-4 text-center">暂无待指派工单</div>}
        </div>

        {/* Right: Active + Completed */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircleOutlined className="text-green-500" />
            <span className="font-semibold">处理中/已完成</span>
            <Badge count={activeOrders.length} color="#1677ff" />
          </div>
          {[...activeOrders, ...completedOrders].map((wo: WorkOrder) => (
            <Card key={wo.id} size="small" className="mb-3">
              <div className="flex items-center justify-between mb-2">
                <strong>
                  {wo.type === 'delivery' ? '📦' : '🔧'} {wo.content}
                </strong>
                <span className={`text-xs font-semibold ${wo.status === 'completed' ? 'text-green-500' : 'text-yellow-600'}`}>
                  {wo.status === 'completed' ? '✅ 已完成' : '⏳ 处理中'}
                </span>
              </div>
              {wo.assigned_resource && (
                <div className="text-xs text-gray-500 mb-2">指派：{wo.assigned_resource}</div>
              )}
              {wo.status === 'processing' && (
                <Button size="small" type="primary" danger onClick={() => handleComplete(wo.id)}>
                  确认完成
                </Button>
              )}
            </Card>
          ))}
          {activeOrders.length === 0 && completedOrders.length === 0 && (
            <div className="text-gray-400 text-sm py-4 text-center">暂无工单</div>
          )}
        </div>
      </div>
    </div>
  )
}
