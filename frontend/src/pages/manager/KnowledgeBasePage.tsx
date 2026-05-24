import { useState, useEffect } from 'react'
import { Card, Upload, Button, List, Tag, InputNumber, message } from 'antd'
import { UploadOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import apiClient from '../../api/client'

interface RAGDoc {
  id: string
  title: string
  file_name: string
  chunks: number
  uploaded_at: string
  vectorized_at: string | null
}

export default function KnowledgeBasePage() {
  const [threshold, setThreshold] = useState(50)
  const [documents, setDocuments] = useState<RAGDoc[]>([])
  const [uploading, setUploading] = useState(false)

  const fetchDocuments = async () => {
    try {
      const { data } = await apiClient.get('/api/rag/documents')
      setDocuments(Array.isArray(data) ? data : [])
    } catch {
      setDocuments([])
    }
  }

  useEffect(() => { fetchDocuments() }, [])

  const handleUpload = async (file: UploadFile) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file as unknown as File)
      await apiClient.post('/api/rag/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      message.success('文档上传成功，正在向量化...')
      fetchDocuments()
    } catch {
      message.error('上传失败')
    } finally {
      setUploading(false)
    }
    return false
  }

  const handleDelete = async (id: string) => {
    try {
      await apiClient.delete(`/api/rag/documents/${id}`)
      message.success('文档已删除')
      fetchDocuments()
    } catch {
      message.error('删除失败')
    }
  }

  const handleSaveThreshold = async () => {
    try {
      await apiClient.post('/api/ai/safety-threshold', { threshold })
      message.success('安全阈值已保存')
    } catch {
      message.error('保存失败')
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">📚 知识库管理 (RAG控制台)</h2>

      <Card className="mb-4">
        <Upload.Dragger
          accept=".md"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
        >
          <UploadOutlined className="text-2xl text-gray-400" />
          <p className="text-sm text-gray-500 mt-2">{uploading ? '上传中...' : '点击或拖拽上传 Markdown 文档'}</p>
          <p className="text-xs text-gray-300">支持 .md 格式 | 上传后自动切片 → 向量化 → 写入 pgvector</p>
        </Upload.Dragger>
      </Card>

      <Card title="已上传文档" className="mb-4">
        <List
          dataSource={documents}
          locale={{ emptyText: '暂无已上传文档' }}
          renderItem={(doc) => (
            <List.Item
              actions={[
                <Button type="text" danger icon={<DeleteOutlined />} size="small" key="delete"
                  onClick={() => handleDelete(doc.id)} />,
              ]}
            >
              <FileTextOutlined className="text-blue-500 mr-2" />
              <span className="text-sm">{doc.file_name || doc.title}</span>
              <span className="text-xs text-gray-400 ml-2">{doc.chunks} 切片</span>
              <Tag color={doc.vectorized_at ? 'green' : 'gold'} className="ml-2 text-xs">
                {doc.vectorized_at ? '已向量化' : '处理中'}
              </Tag>
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
          <Button type="primary" size="small" onClick={handleSaveThreshold}>保存设置</Button>
          <span className="text-xs text-gray-400">无论市场多火爆，溢价绝不允许超过基础价的此比例</span>
        </div>
      </Card>
    </div>
  )
}
