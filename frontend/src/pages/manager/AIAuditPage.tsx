import { useEffect, useState } from 'react'
import { Card, Tag, Spin, Button, List, message } from 'antd'
import { WarningOutlined, BulbOutlined, ReloadOutlined } from '@ant-design/icons'
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
  const [reports, setReports] = useState<AuditReport[]>([])
  const [activeIdx, setActiveIdx] = useState(0)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [seeding, setSeeding] = useState(false)

  const fetchReports = async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/api/admin/audit-reports')
      setReports(data)
      setActiveIdx(0)
    } catch {
      message.error('获取审计报告失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReports() }, [])

  const handleTrigger = async () => {
    setTriggering(true)
    try {
      const { data } = await apiClient.post('/api/admin/audit-reports/trigger')
      if (data.skipped) {
        message.info(`今日报告已存在（${data.date}），跳过生成`)
      } else {
        message.success(`审计完成，发现 ${data.anomalies_count} 个异常`)
      }
      await fetchReports()
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || '未知错误'
      message.error(`审计触发失败: ${detail}`)
    } finally {
      setTriggering(false)
    }
  }

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await apiClient.post('/api/admin/seed-audit-test')
      message.success('测试工单已注入，请点击「立即审计」生成报告')
    } catch {
      message.error('注入失败')
    } finally {
      setSeeding(false)
    }
  }

  if (loading) {
    return <div className="flex justify-center py-20"><Spin size="large" description="加载审计报告..." /></div>
  }

  if (reports.length === 0) {
    return (
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">🤖 AI运营反思与审计看板</h2>
          <Button type="primary" icon={<ReloadOutlined />} loading={triggering} onClick={handleTrigger}>
            立即审计
          </Button>
        </div>
        <Card className="bg-blue-50 border-blue-200">
          <p className="text-gray-600 text-center py-8">
            📋 暂无审计报告。点击「立即审计」手动触发，或等待每日凌晨 4:00 自动生成。
          </p>
        </Card>
      </div>
    )
  }

  const report = reports[activeIdx] || reports[0]
  const anomalies = report?.anomalies || []
  const content = report?.content || {}
  const anomalyItems = Array.isArray(anomalies) ? anomalies : Object.values(anomalies)

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">🤖 AI运营反思与审计看板</h2>
        <div className="flex gap-2">
          <Button loading={seeding} onClick={handleSeed}>
            注入测试数据
          </Button>
          <Button type="primary" icon={<ReloadOutlined />} loading={triggering} onClick={handleTrigger}>
            立即审计
          </Button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, minHeight: 400 }}>
        {/* 左侧：报告列表 */}
        <div style={{ width: 256, flexShrink: 0 }}>
          <Card bodyStyle={{ padding: 0 }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0', fontWeight: 600, fontSize: 14, color: '#666' }}>
              历史报告 ({reports.length})
            </div>
            {reports.map((item, idx) => (
              <div
                key={item.id}
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  borderBottom: '1px solid #fafafa',
                  background: idx === activeIdx ? '#e6f4ff' : 'transparent',
                  borderLeft: idx === activeIdx ? '3px solid #1677ff' : '3px solid transparent',
                }}
                onClick={() => setActiveIdx(idx)}
              >
                <div style={{ fontSize: 14, fontWeight: 500 }}>{item.date}</div>
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  {item.anomalies ? (Array.isArray(item.anomalies) ? item.anomalies.length : Object.keys(item.anomalies).length) : 0} 个异常
                </div>
              </div>
            ))}
          </Card>
        </div>

        {/* 右侧：报告详情 */}
        <div style={{ flex: 1 }}>
          <Card style={{ marginBottom: 16, background: '#fffbe6', borderColor: '#ffe58f' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#d48806', marginBottom: 8 }}>📊 运营异常与客户流失风险审计报告</h3>
            <p style={{ fontSize: 12, color: '#999' }}>
              生成时间：{report ? new Date(report.generated_at).toLocaleString('zh-CN') : '-'} | 引擎：DeepSeek Reflection
            </p>
          </Card>

          <Card title={<span style={{ color: '#ff4d4f' }}><WarningOutlined /> 服务异常 TOP 排行</span>} style={{ marginBottom: 16 }}>
            {anomalyItems.length > 0 ? anomalyItems.map((item: Anomaly, idx: number) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 12, borderRadius: 8, marginBottom: 8, background: '#fef2f2' }}>
                <span style={{ fontSize: 18 }}>{['🥇', '🥈', '🥉'][idx] || '📌'}</span>
                <span style={{ fontWeight: 700, fontSize: 16 }}>{item.staff || item.room || '-'}</span>
                <Tag color="red">{item.issue || '异常'}</Tag>
                {item.overtime_count !== undefined && (
                  <span style={{ fontWeight: 700, fontSize: 18, color: '#ff4d4f' }}>{item.overtime_count} 次</span>
                )}
                <span style={{ fontSize: 12, color: '#999' }}>{item.risk || ''}</span>
              </div>
            )) : (
              <p style={{ color: '#999', textAlign: 'center', padding: 16 }}>无异常数据</p>
            )}
          </Card>

          {content.risk_rooms && (
            <Card style={{ marginBottom: 16, background: '#fff2f0', borderColor: '#ffccc7' }}>
              <h4 style={{ fontWeight: 600, color: '#ff4d4f', marginBottom: 8 }}><WarningOutlined /> 高客诉风险房间</h4>
              <p style={{ fontSize: 14, color: '#666' }}>{String(content.risk_rooms)}</p>
            </Card>
          )}

          {content.recommendations && (
            <Card style={{ marginBottom: 16, background: '#f6ffed', borderColor: '#b7eb8f' }}>
              <h4 style={{ fontWeight: 600, color: '#52c41a', marginBottom: 8 }}><BulbOutlined /> AI整改建议</h4>
              <p style={{ fontSize: 14, color: '#666' }}>{String(content.recommendations)}</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
