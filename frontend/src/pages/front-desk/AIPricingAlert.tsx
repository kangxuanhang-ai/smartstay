import { Modal, message } from 'antd'

interface Props {
  open: boolean
  originalPrice: number
  suggestedPrice: number
  reason: string
  logId: string
  onClose: () => void
}

export default function AIPricingAlert({ open, originalPrice, suggestedPrice, reason, logId, onClose }: Props) {
  const handleApprove = async () => {
    try {
      const apiClient = (await import('../../api/client')).default
      await apiClient.put(`/api/ai/pricing/${logId}/approve`)
      message.success('调价已批准')
      onClose()
    } catch {
      message.error('操作失败')
    }
  }

  const handleReject = async () => {
    try {
      const apiClient = (await import('../../api/client')).default
      await apiClient.put(`/api/ai/pricing/${logId}/reject`)
      message.success('已拒绝调价')
      onClose()
    } catch {
      message.error('操作失败')
    }
  }

  const increase = Math.round(((suggestedPrice - originalPrice) / originalPrice) * 100)

  return (
    <Modal
      title={<span className="text-lg font-bold text-yellow-600">🤖 AI 定价建议</span>}
      open={open}
      onCancel={onClose}
      footer={[
        <button key="reject" onClick={handleReject} className="px-6 py-2 bg-red-500 text-white rounded-lg font-semibold hover:bg-red-600">
          ❌ 拒绝
        </button>,
        <button key="approve" onClick={handleApprove} className="px-6 py-2 bg-green-500 text-white rounded-lg font-semibold hover:bg-green-600 ml-3">
          ✅ 批准调价
        </button>,
      ]}
      centered
      mask={{ closable: false }}
    >
      <div className="text-center py-4">
        <p className="text-gray-500 mb-4">{reason}</p>
        <div className="flex items-center justify-center gap-6 mb-4">
          <div className="text-center">
            <p className="text-xs text-gray-400">原价</p>
            <p className="text-2xl font-bold text-gray-400 line-through">¥{Math.round(originalPrice / 100)}</p>
          </div>
          <span className="text-2xl text-yellow-500">→</span>
          <div className="text-center">
            <p className="text-xs text-yellow-500">建议价</p>
            <p className="text-2xl font-bold text-red-500">¥{Math.round(suggestedPrice / 100)}</p>
          </div>
        </div>
        <p className="text-sm text-gray-400">涨幅 {increase}% · 不超过安全阈值 50%</p>
      </div>
    </Modal>
  )
}
