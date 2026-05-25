import { useEffect, useState } from 'react'
import { Card, Tag, Spin } from 'antd'
import { WarningOutlined, BulbOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'

interface Anomaly {
  room?: string
  issue?: string
  risk?: string
  staff?: string
  overtime_count?: number
}

interface AuditReport {
  id: string
  date: string
  content: Record<string, unknown> | null
  anomalies: Anomaly[] | null
  generated_at: string
}

export default function AIAuditPage() {
  const [report, setReport] = useState<AuditReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get('/api/admin/audit-reports')
      .then(({ data }) => {
        if (data.length > 0) setReport(data[0])
      }).catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-20"><Spin size="large" tip="加载审计报告..." /></div>

  if (!report) {
    return (
      <div>
        <h2 className="text-lg font-semibold mb-4">🤖 AI运营反思与审计看板</h2>
        <Card className="bg-blue-50 border-blue-200">
          <p className="text-gray-600 text-center py-8">
            📋 暂无审计报告。AI 审计 Agent 将在每日凌晨 4:00 自动生成。<br />
            <span className="text-sm text-gray-400">（Phase 4 AI引擎完成后可用）</span>
          </p>
        </Card>
      </div>
    )
  }

  const anomalies = report.anomalies || []
  const content = report.content || {}

  const anomalyItems = Array.isArray(anomalies)
    ? anomalies
    : Object.values(anomalies)

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">🤖 AI运营反思与审计看板</h2>

      <Card className="mb-4 bg-yellow-50 border-yellow-300">
        <h3 className="text-base font-bold text-yellow-700 mb-2">📊 运营异常与客户流失风险审计报告</h3>
        <p className="text-xs text-gray-400">
          生成时间：{new Date(report.generated_at).toLocaleString('zh-CN')} | 引擎：DeepSeek Reflection
        </p>
      </Card>

      <Card
        title={<span className="text-red-500"><WarningOutlined /> 服务异常 TOP 排行</span>}
        className="mb-4"
      >
        {anomalyItems.length > 0 ? anomalyItems.map((item: Anomaly, idx: number) => (
          <div key={idx} className="flex items-center gap-4 p-3 rounded-md mb-2" style={{ background: '#fef2f2' }}>
            <span className="text-lg">{['🥇', '🥈', '🥉'][idx] || '📌'}</span>
            <span className="font-bold text-base">{item.staff || item.room || '-'}</span>
            <Tag color="red">{item.issue || '异常'}</Tag>
            {item.overtime_count !== undefined && (
              <span className="font-bold text-lg text-red-500">{item.overtime_count} 次</span>
            )}
            <span className="text-xs text-gray-400">{item.risk || ''}</span>
          </div>
        )) : (
          <p className="text-gray-400 text-center py-4">无异常数据</p>
        )}
      </Card>

      {content.risk_rooms && (
        <Card className="mb-4 bg-red-50 border-red-200">
          <h4 className="font-semibold text-red-500 mb-2"><WarningOutlined /> 高客诉风险房间</h4>
          <p className="text-sm text-gray-600">{String(content.risk_rooms)}</p>
        </Card>
      )}

      {content.recommendations && (
        <Card className="mb-4 bg-green-50 border-green-200">
          <h4 className="font-semibold text-green-500 mb-2"><BulbOutlined /> AI整改建议</h4>
          <p className="text-sm text-gray-600">{String(content.recommendations)}</p>
        </Card>
      )}
    </div>
  )
}
