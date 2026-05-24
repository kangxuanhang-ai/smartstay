import { useState } from 'react'
import { Modal, Form, Input, Select, message } from 'antd'
import apiClient from '../../api/client'

interface Props {
  roomId: string
  open: boolean
  onClose: () => void
}

export default function CheckInModal({ roomId, open, onClose }: Props) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const onOk = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      await apiClient.post('/api/orders/checkin', { ...values, room_id: roomId })
      message.success('开房成功 · 原子事务完成')
      form.resetFields()
      onClose()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      message.error(axiosErr?.response?.data?.detail || '开房失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="📝 线下入住登记"
      open={open}
      onOk={onOk}
      onCancel={onClose}
      confirmLoading={loading}
      okText="确认开房 (原子事务)"
      cancelText="取消"
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
          <Input placeholder="请输入住客姓名" />
        </Form.Item>
        <Form.Item name="id_card" label="身份证号" rules={[{ required: true }]}>
          <Input placeholder="请输入18位身份证号" />
        </Form.Item>
        <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
          <Input placeholder="请输入手机号码" />
        </Form.Item>
        <Form.Item name="source" label="订单来源" initialValue="self_app">
          <Select
            options={[
              { value: 'self_app', label: '自家App' },
              { value: 'ctrip', label: '携程' },
              { value: 'meituan', label: '美团' },
            ]}
          />
        </Form.Item>
      </Form>
      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700 mt-2">
        ⚡ 原子事务：查/建用户 → 创建订单 → 改房态OCCUPIED。任一步失败全量回滚。
      </div>
    </Modal>
  )
}
