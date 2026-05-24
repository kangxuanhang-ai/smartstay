import { useState } from 'react'
import { Card, Upload, Button, List, Tag, InputNumber, message } from 'antd'
import { UploadOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons'

export default function KnowledgeBasePage() {
  const [threshold, setThreshold] = useState(50)
  const [documents] = useState([
    { name: '酒店最新节假日服务标准.md', chunks: 120, status: '已向量化', color: '#52c41a' },
    { name: '泳池安全须知与应急预案.md', chunks: 85, status: '已向量化', color: '#52c41a' },
    { name: '中西餐厅菜单与推荐话术.md', chunks: 67, status: '已向量化', color: '#52c41a' },
  ])

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">📚 知识库管理 (RAG控制台)</h2>

      <Card className="mb-4">
        <Upload.Dragger
          accept=".md"
          beforeUpload={() => false}
          showUploadList={false}
        >
          <UploadOutlined className="text-2xl text-gray-400" />
          <p className="text-sm text-gray-500 mt-2">点击或拖拽上传 Markdown 文档</p>
          <p className="text-xs text-gray-300">支持 .md 格式 | 上传后自动切片 → 向量化 → 写入 pgvector</p>
        </Upload.Dragger>
      </Card>

      <Card title="已上传文档" className="mb-4">
        <List
          dataSource={documents}
          renderItem={(doc) => (
            <List.Item
              actions={[
                <Button type="text" danger icon={<DeleteOutlined />} size="small" key="delete" />,
              ]}
            >
              <FileTextOutlined className="text-blue-500 mr-2" />
              <span className="text-sm">{doc.name}</span>
              <span className="text-xs text-gray-400 ml-2">{doc.chunks} 切片</span>
              <Tag color={doc.color} className="ml-2 text-xs">{doc.status}</Tag>
            </List.Item>
          )}
        />
      </Card>

      <Card
        title={<span className="text-green-600">🛡️ AI安全护栏设置</span>}
        className="bg-green-50 border-green-200"
      >
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">最大溢价幅度：</span>
          <InputNumber min={0} max={100} value={threshold} onChange={(v) => setThreshold(v || 50)} addonAfter="%" />
          <Button type="primary" size="small" onClick={() => message.success('安全阈值已更新')}>保存设置</Button>
          <span className="text-xs text-gray-400">无论市场多火爆，溢价绝不允许超过基础价的此比例</span>
        </div>
      </Card>
    </div>
  )
}
