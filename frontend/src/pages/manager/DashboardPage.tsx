import { Card, Statistic } from 'antd'
import { ArrowUpOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useState, useEffect } from 'react'
import apiClient from '../../api/client'

interface DashboardStats {
  occupancy: number
  occupied: number
  total_rooms: number
  revpar: number
  revenue: number
  today_orders: number
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    occupancy: 0, occupied: 0, total_rooms: 0, revpar: 0, revenue: 0, today_orders: 0,
  })

  useEffect(() => {
    apiClient.get('/api/admin/dashboard').then(({ data }) => setStats(data))
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
        { value: 30, name: '携程', itemStyle: { color: '#22c55e' } },
        { value: 20, name: '美团', itemStyle: { color: '#f59e0b' } },
      ],
      label: { show: true, formatter: '{b}\n{d}%' },
    }],
  }

  const revenueInYuan = stats.revenue ? (stats.revenue / 100).toFixed(0) : '0'
  const revparInYuan = stats.revpar ? (stats.revpar / 100).toFixed(0) : '0'

  return (
    <div>
      <h2 className="!text-xl !font-bold !text-slate-800 !mb-6">📊 总店长决策大盘</h2>

      <div className="!grid !grid-cols-1 sm:!grid-cols-3 !gap-4 !mb-6">
        <Card className="!shadow-sm !border !border-slate-200 hover:!shadow-md !transition-shadow">
          <Statistic title={`入住率 (${stats.occupied}/${stats.total_rooms})`}
            value={stats.occupancy} suffix="%"
            valueStyle={{ color: '#1677ff', fontSize: 32 }} prefix={<ArrowUpOutlined />} />
        </Card>
        <Card className="!shadow-sm !border !border-slate-200 hover:!shadow-md !transition-shadow">
          <Statistic title="RevPAR (每间可售房收入)" value={revparInYuan} prefix="¥"
            valueStyle={{ color: '#22c55e', fontSize: 32 }} />
        </Card>
        <Card className="!shadow-sm !border !border-slate-200 hover:!shadow-md !transition-shadow">
          <Statistic title="今日流水" value={revenueInYuan} prefix="¥"
            valueStyle={{ color: '#f59e0b', fontSize: 32 }} />
        </Card>
      </div>

      <div className="!grid !grid-cols-1 xl:!grid-cols-2 !gap-6">
        <Card title={<span className="!font-semibold !text-slate-800">📈 全天流水走势</span>}
          className="!shadow-sm !border !border-slate-200"
        >
          <ReactECharts option={barOption} style={{ width: '100%' }} />
        </Card>
        <Card title={<span className="!font-semibold !text-slate-800">🥧 订单渠道占比</span>}
          className="!shadow-sm !border !border-slate-200"
        >
          <ReactECharts option={pieOption} style={{ width: '100%' }} />
        </Card>
      </div>
    </div>
  )
}
