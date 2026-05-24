import { Modal } from 'antd'
import apiClient from '../../api/client'

interface WorkOrder {
  id: string
  room_id: string
  type: string
  content: string
  created_at: string
}

interface Props {
  open: boolean
  workOrder: WorkOrder | null
  onClose: () => void
  onAccept: () => void
}

export default function NewWorkOrderAlert({ open, workOrder, onClose, onAccept }: Props) {
  if (!workOrder) return null

  const handleAccept = async () => {
    try {
      await apiClient.put(`/api/work-orders/${workOrder.id}/accept`)
      onAccept()
    } catch {
      onClose()
    }
  }

  return (
    <Modal
      title={<span className="text-lg font-bold text-blue-500">🔔 新工单提醒 · WebSocket实时推送</span>}
      open={open}
      onCancel={onClose}
      footer={[
        <button key="later" onClick={onClose} className="px-6 py-2 bg-gray-100 text-gray-600 rounded-lg border border-gray-200">
          稍后处理
        </button>,
        <button key="accept" onClick={handleAccept} className="px-6 py-2 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 ml-3">
          ✅ 立即接单
        </button>,
      ]}
      centered
    >
      <div className="py-4">
        <p className="text-xs text-gray-400 mb-4">
          来自 AI虚拟管家 · {new Date(workOrder.created_at).toLocaleTimeString()} · 🔊 系统提示音已播放
        </p>
        <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
          <span className="text-2xl">{workOrder.type === 'delivery' ? '📦' : '🔧'}</span>
          <div>
            <p className="font-semibold text-base">
              {workOrder.type === 'delivery' ? '送物工单' : '报修工单'} · {workOrder.content}
            </p>
            <p className="text-sm text-gray-500">房间 ID: {workOrder.room_id?.substring(0, 8)}...</p>
          </div>
        </div>
      </div>
    </Modal>
  )
}
