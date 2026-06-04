import { useEffect } from 'react'
import { notification } from 'antd'
import { WarningOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'

interface ComplaintData {
  room_number: string
  room_id: string
  guest_name: string
  message: string
}

export default function ComplaintAlert() {
  const ws = useWebSocket()
  const navigate = useNavigate()
  const [api, contextHolder] = notification.useNotification()

  useEffect(() => {
    const unsub = ws.on('complaint.alert', (data: ComplaintData) => {
      api.error({
        message: `🚨 住客投诉 - ${data.room_number}`,
        description: (
          <div>
            <p><strong>住客：</strong>{data.guest_name}</p>
            <p><strong>内容：</strong>{data.message}</p>
          </div>
        ),
        duration: 0, // 不自动关闭
        icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
        btn: (
          <a onClick={() => {
            navigate('/front-desk/work-orders')
            api.destroy()
          }}>
            查看工单
          </a>
        ),
      })
    })
    return unsub
  }, [ws, api, navigate])

  return contextHolder
}