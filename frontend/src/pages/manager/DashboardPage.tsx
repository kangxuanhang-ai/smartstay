import { Card, Statistic, Row, Col } from 'antd'
import { ArrowUpOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useState, useEffect } from 'react'
import apiClient from '../../api/client'

export default function DashboardPage() {
  const [stats, setStats] = useState({ occupancy: 80, revpar: 240, revenue: 12560 })

  useEffect(() => {
    apiClient.get('/api/rooms/').then(({ data }) => {
      const occupied = data.filter((r: { status: string }) => r.status === 'occupied').length
      setStats((s) => ({ ...s, occupancy: Math.round((occupied / data.length) * 100) }))
    })
  }, [])

  const barOption = {
    xAxis: { type: 'category', data: ['00', '02', '04', '06', '08', '10', '12', '14', '16', '18', '20', '22'] },
    yAxis: { type: 'value' },
    series: [{ data: [0, 0, 0, 15, 42, 78, 115, 98, 72, 58, 35, 10], type: 'bar', itemStyle: { color: '#1677FF' }, barWidth: 12 }],
    grid: { top: 10, right: 10, bottom: 20, left: 40 },
  }

  const pieOption = {
    series: [{
      type: 'pie', radius: ['55%', '80%'],
      data: [
        { value: 50, name: '自家App', itemStyle: { color: '#1677FF' } },
        { value: 30, name: '携程', itemStyle: { color: '#52C41A' } },
        { value: 20, name: '美团', itemStyle: { color: '#FAAD14' } },
      ],
      label: { show: true, formatter: '{b}\n{d}%' },
    }],
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">📊 总店长决策大盘</h2>

      <Row gutter={16} className="mb-4">
        <Col span={8}>
          <Card>
            <Statistic title="实时入住率" value={stats.occupancy} suffix="%" valueStyle={{ color: '#1677FF', fontSize: 32 }} prefix={<ArrowUpOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="RevPAR" value={stats.revpar} prefix="¥" valueStyle={{ color: '#52C41A', fontSize: 32 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="今日流水" value={stats.revenue} prefix="¥" valueStyle={{ color: '#FAAD14', fontSize: 32 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={14}>
          <Card title="📈 全天流水走势" className="mb-4">
            <ReactECharts option={barOption} style={{ height: 260 }} />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="🥧 订单渠道占比" className="mb-4">
            <ReactECharts option={pieOption} style={{ height: 260 }} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
