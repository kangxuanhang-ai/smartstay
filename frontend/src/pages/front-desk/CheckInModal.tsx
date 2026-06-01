import { useState, useRef } from 'react'
import { Modal, Form, Input, Select, Button, message, Upload, Space, Tag } from 'antd'
import { UploadOutlined, CameraOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'
import FaceCapture from './FaceCapture'

interface Props {
  roomId: string
  open: boolean
  onClose: () => void
}

export default function CheckInModal({ roomId, open, onClose }: Props) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  // Face verification state
  const [idCardFile, setIdCardFile] = useState<File | null>(null)
  const [idCardImage, setIdCardImage] = useState<string | null>(null)
  const [liveFaceBlob, setLiveFaceBlob] = useState<Blob | null>(null)
  const [faceVerified, setFaceVerified] = useState(false)
  const [faceVerifying, setFaceVerifying] = useState(false)
  const [faceError, setFaceError] = useState<string | null>(null)
  const [showFaceCapture, setShowFaceCapture] = useState(false)
  const [idCardData, setIdCardData] = useState<{ name: string; id_card: string; face_url: string } | null>(null)
  const [ocrLoading, setOcrLoading] = useState(false)
  const guestIdRef = useRef<string | null>(null)

  const handleIdCardUpload = async (file: File) => {
    setIdCardFile(file)
    setIdCardImage(URL.createObjectURL(file))
    setOcrLoading(true)
    setFaceError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await apiClient.post('/api/face/detect', formData)
      if (res.data.face_count > 0) {
        message.success('身份证照片检测通过')
      } else {
        setFaceError('未在照片中检测到人脸，请重新上传')
        message.warning('未检测到人脸')
      }
    } catch {
      setFaceError('身份证照片检测失败，请重试')
      message.error('身份证检测失败')
    } finally {
      setOcrLoading(false)
    }

    return false // Prevent default upload
  }

  const handleCaptureRetry = () => {
    setLiveFaceBlob(null)
    setFaceVerified(false)
    setFaceError(null)
  }

  const handleVerify = async () => {
    if (!idCardFile || !liveFaceBlob) return
    setFaceVerifying(true)
    setFaceError(null)

    try {
      const formData = new FormData()
      formData.append('id_card_image', idCardFile)
      formData.append('live_image', new File([liveFaceBlob], 'face.jpg', { type: 'image/jpeg' }))
      const res = await apiClient.post('/api/face/verify', formData)
      if (res.data.matched) {
        setFaceVerified(true)
        message.success(`人脸匹配成功 · 置信度 ${(res.data.confidence * 100).toFixed(1)}%`)
      } else {
        setFaceError(`人脸与身份证不匹配（置信度 ${(res.data.confidence * 100).toFixed(1)}%），请重试`)
        message.error('人脸匹配失败')
      }
    } catch {
      setFaceError('验证服务暂时不可用，请稍后重试')
      message.error('人脸验证失败')
    } finally {
      setFaceVerifying(false)
    }
  }

  const resetFaceState = () => {
    setIdCardFile(null)
    setIdCardImage(null)
    setLiveFaceBlob(null)
    setFaceVerified(false)
    setFaceVerifying(false)
    setFaceError(null)
    setShowFaceCapture(false)
    setIdCardData(null)
    setOcrLoading(false)
    guestIdRef.current = null
  }

  const onOk = async () => {
    const values = await form.validateFields()
    if (!faceVerified) {
      message.warning('请先完成人脸验证')
      return
    }
    setLoading(true)
    try {
      const res = await apiClient.post('/api/orders/checkin', { ...values, room_id: roomId })
      guestIdRef.current = res.data?.guest_id || res.data?.user_id || null

      // Register face to Aliyun face database after successful check-in
      if (guestIdRef.current && liveFaceBlob) {
        try {
          const faceFormData = new FormData()
          faceFormData.append('guest_id', guestIdRef.current)
          faceFormData.append('file', new File([liveFaceBlob], 'face.jpg', { type: 'image/jpeg' }))
          await apiClient.post('/api/face/register', faceFormData)
        } catch {
          message.warning('开房成功，但人脸注册失败，可稍后重试')
        }
      }

      message.success('开房成功 · 原子事务完成')
      form.resetFields()
      resetFaceState()
      onClose()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      message.error(axiosErr?.response?.data?.detail || '开房失败')
    } finally {
      setLoading(false)
    }
  }

  const handleModalClose = () => {
    form.resetFields()
    resetFaceState()
    onClose()
  }

  return (
    <Modal
      title="📝 线下入住登记"
      open={open}
      onOk={onOk}
      onCancel={handleModalClose}
      confirmLoading={loading}
      okText="确认开房 (原子事务)"
      cancelText="取消"
      width={560}
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

      {/* Face verification section */}
      <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, marginTop: 8 }}>
        <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>人脸录入验证</div>

        {/* Step 1: Upload ID card */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>1. 上传身份证照片</div>
          <Space direction="vertical" style={{ width: '100%' }}>
            {!idCardImage ? (
              <Upload
                accept="image/*"
                showUploadList={false}
                beforeUpload={handleIdCardUpload}
              >
                <Button icon={<UploadOutlined />} loading={ocrLoading}>
                  上传身份证正面照片
                </Button>
              </Upload>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <img src={idCardImage} alt="id card" style={{ width: 120, height: 'auto', borderRadius: 4, border: '1px solid #d9d9d9' }} />
                <Button size="small" onClick={() => { setIdCardFile(null); setIdCardImage(null); setFaceError(null) }}>
                  重新上传
                </Button>
              </div>
            )}
          </Space>
        </div>

        {/* Step 2: Capture live face */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>2. 拍摄住客本人人脸</div>
          {!showFaceCapture ? (
            <Button
              icon={<CameraOutlined />}
              onClick={() => setShowFaceCapture(true)}
              disabled={!idCardImage}
            >
              录入住客人脸
            </Button>
          ) : (
            <FaceCapture
              onCapture={(blob) => setLiveFaceBlob(blob)}
              onRetry={handleCaptureRetry}
              captured={liveFaceBlob}
            />
          )}
        </div>

        {/* Step 3: Verify */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>3. 验证人脸匹配</div>
          <Space>
            <Button
              type="primary"
              onClick={handleVerify}
              disabled={!idCardFile || !liveFaceBlob || faceVerified}
              loading={faceVerifying}
            >
              开始验证
            </Button>
            {faceVerified && (
              <Tag icon={<CheckCircleOutlined />} color="success">
                验证通过
              </Tag>
            )}
            {faceError && !faceVerified && (
              <Tag icon={<CloseCircleOutlined />} color="error">
                验证失败
              </Tag>
            )}
          </Space>
          {faceError && !faceVerifying && (
            <div style={{ color: '#ff4d4f', fontSize: 12, marginTop: 4 }}>{faceError}</div>
          )}
          {faceVerifying && (
            <div style={{ color: '#1677ff', fontSize: 12, marginTop: 4 }}>
              <LoadingOutlined style={{ marginRight: 4 }} />正在验证中，请稍候...
            </div>
          )}
        </div>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-700 mt-2">
        ⚡ 原子事务：查/建用户 → 创建订单 → 改房态OCCUPIED。任一步失败全量回滚。
      </div>
    </Modal>
  )
}
