import { useState, useEffect } from 'react'
import { Card, Tag, Dropdown, message } from 'antd'
import { HomeOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'
import CheckInModal from './CheckInModal'

interface Room {
  id: string
  room_number: string
  room_type: string
  status: string
  floor: number
  current_price: number
}

const STATUS_COLORS: Record<string, string> = {
  vacant: '#22c55e',
  occupied: '#ef4444',
  dirty: '#f59e0b',
  maintenance: '#6b7280',
}

const STATUS_LABELS: Record<string, string> = {
  vacant: '空房',
  occupied: '有人住',
  dirty: '脏房',
  maintenance: '维修中',
}

const ROOM_TYPE_LABELS: Record<string, string> = {
  big_bed: '大床房',
  twin: '双床房',
  suite: '套房',
}

export default function RoomGridPage() {
  const [rooms, setRooms] = useState<Room[]>([])
  const [checkInRoom, setCheckInRoom] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    apiClient.get('/api/rooms/').then(({ data }) => setRooms(data)).catch(() => message.error('加载房间数据失败'))
  }, [refreshKey])

  const handleStatusChange = async (roomId: string, status: string) => {
    try {
      await apiClient.put(`/api/rooms/${roomId}/status`, { status })
      message.success('房间状态已更新')
      setRefreshKey((k) => k + 1)
    } catch {
      message.error('操作失败')
    }
  }

  const handleCheckout = async (roomId: string) => {
    try {
      const { data } = await apiClient.get(`/api/orders/room/${roomId}/active`)
      await apiClient.put(`/api/orders/${data.id}/checkout`)
      message.success('退房成功')
      setRefreshKey((k) => k + 1)
    } catch {
      message.error('退房失败')
    }
  }

  const stats = {
    vacant: rooms.filter((r) => r.status === 'vacant').length,
    occupied: rooms.filter((r) => r.status === 'occupied').length,
    dirty: rooms.filter((r) => r.status === 'dirty').length,
    maintenance: rooms.filter((r) => r.status === 'maintenance').length,
  }

  return (
    <div>
      <div className="!flex !flex-wrap !justify-between !items-center !gap-3 !mb-6">
        <h2 className="!text-xl !font-bold !text-slate-800">📊 实时房态全景</h2>
        <div className="!flex !flex-wrap !gap-2">
          {Object.entries(stats).map(([key, value]) => (
            <Card size="small" key={key}
              styles={{ body: { padding: '8px 16px' } }}
              className="!shadow-sm !border !border-slate-200"
            >
              <span className="!text-lg !font-bold" style={{ color: STATUS_COLORS[key] }}>{value}</span>
              <span className="!text-xs !text-slate-500 !ml-2">{STATUS_LABELS[key]}</span>
            </Card>
          ))}
        </div>
      </div>

      <div className="!grid !grid-cols-1 sm:!grid-cols-2 md:!grid-cols-3 lg:!grid-cols-4 xl:!grid-cols-5 !gap-4">
        {rooms.map((room) => (
          <Dropdown
            key={room.id}
            trigger={['contextMenu']}
            menu={{
              items: [
                ...(room.status === 'vacant'
                  ? [{ key: 'checkin', label: '🚪 快捷开房', onClick: () => setCheckInRoom(room.id) }]
                  : []),
                ...(room.status === 'occupied'
                  ? [{ key: 'checkout', label: '🏃 办理退房', onClick: () => handleCheckout(room.id) }]
                  : []),
                { key: 'dirty', label: '🧹 设为脏房', onClick: () => handleStatusChange(room.id, 'dirty') },
                { key: 'lock', label: '🔒 一键锁房/解锁', onClick: () => handleStatusChange(room.id, 'maintenance') },
                { key: 'unlock', label: '🟢 设为空房', onClick: () => handleStatusChange(room.id, 'vacant') },
              ],
            }}
          >
            <Card
              size="small"
              hoverable
              className="!shadow-sm !border-2 !border-slate-200 hover:!shadow-md hover:!border-slate-300 !transition-all !duration-200"
              style={{ borderColor: STATUS_COLORS[room.status] || '#d9d9d9' }}
              styles={{ body: { padding: '16px 12px', textAlign: 'center' } }}
            >
              <div className="!flex !items-center !justify-center !gap-1.5 !mb-2 !truncate">
                <HomeOutlined style={{ color: STATUS_COLORS[room.status], fontSize: 16, flexShrink: 0 }} />
                <strong className="!text-xl !font-bold !text-slate-800 !truncate">{room.room_number}</strong>
              </div>
              <div className="!text-xs !text-slate-500 !mb-2">{ROOM_TYPE_LABELS[room.room_type] || room.room_type}</div>
              <Tag color={STATUS_COLORS[room.status]}>{STATUS_LABELS[room.status]}</Tag>
              <div className="!text-base !font-bold !text-blue-600 !mt-2">
                ¥{Math.round(room.current_price / 100)}
              </div>
            </Card>
          </Dropdown>
        ))}
      </div>

      {checkInRoom && (
        <CheckInModal
          roomId={checkInRoom}
          open={!!checkInRoom}
          onClose={() => {
            setCheckInRoom(null)
            setRefreshKey((k) => k + 1)
          }}
        />
      )}
    </div>
  )
}
