import { Card, Tag } from 'antd'
import { WarningOutlined, BulbOutlined } from '@ant-design/icons'

export default function AIAuditPage() {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">🤖 AI运营反思与审计看板</h2>

      <Card className="mb-4 bg-yellow-50 border-yellow-300">
        <h3 className="text-base font-bold text-yellow-700 mb-2">📊 昨日运营异常与客户流失风险审计报告</h3>
        <p className="text-xs text-gray-400">生成时间：2026-05-23 04:00 | 分析周期：过去24小时 | 引擎：DeepSeek Reflection</p>
      </Card>

      <Card
        title={<span className="text-red-500"><WarningOutlined /> 服务异常 TOP 排行</span>}
        className="mb-4"
      >
        {[
          { rank: '🥇', name: '张阿姨', issue: '服务超时', count: '5 次', detail: '主要集中晚班时段', color: '#ff4d4f' },
          { rank: '🥈', name: '李师傅', issue: '服务超时', count: '3 次', detail: '302房空调维修delay', color: '#faad14' },
          { rank: '🥉', name: '王保洁', issue: '客诉', count: '1 次', detail: '305房毛巾未及时送达', color: '#faad14' },
        ].map((item) => (
          <div key={item.name} className="flex items-center gap-4 p-3 rounded-md mb-2" style={{ background: item.color + '11' }}>
            <span className="text-lg">{item.rank}</span>
            <span className="font-bold text-base">{item.name}</span>
            <Tag color={item.color}>{item.issue}</Tag>
            <span className="font-bold text-lg" style={{ color: item.color }}>{item.count}</span>
            <span className="text-xs text-gray-400">{item.detail}</span>
          </div>
        ))}
      </Card>

      <Card className="mb-4 bg-red-50 border-red-200">
        <h4 className="font-semibold text-red-500 mb-2"><WarningOutlined /> 高客诉风险房间</h4>
        <p className="text-sm text-gray-600">302 房：住客在24小时内连续催促超过3次，客诉流失风险极高。建议安排值班经理上门安抚，赠送果盘/代金券。</p>
      </Card>

      <Card className="mb-4 bg-green-50 border-green-200">
        <h4 className="font-semibold text-green-500 mb-2"><BulbOutlined /> AI整改建议</h4>
        <ol className="text-sm text-gray-600 list-decimal pl-4 space-y-1">
          <li>增加晚班保洁排班，建议19:00-23:00加派1人</li>
          <li>对张阿姨进行服务流程再培训</li>
          <li>302房空调需彻底检修，避免重复报修</li>
        </ol>
      </Card>
    </div>
  )
}
