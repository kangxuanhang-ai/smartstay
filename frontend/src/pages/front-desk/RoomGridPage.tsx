import { useState, useEffect } from 'react'
import { Card, Tag, Dropdown, message, Space } from 'antd'
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
  device_states: Record<string, unknown>
}

const STATUS_COLORS: Record<string, string> = {
  vacant: '#52c41a',
  occupied: '#ff4d4f',
  dirty: '#faad14',
  maintenance: '#8c8c8c',
}

const STATUS_LABELS: Record<string, string> = {
  vacant: 'VACANT',
  occupied: 'OCCUPIED',
  dirty: 'DIRTY',
  maintenance: 'MAINT',
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
    apiClient.get('/api/rooms/').then(({ data }) => setRooms(data))
  }, [refreshKey])

  const handleStatusChange = async (roomId: string, status: string) => {
    try {
      await apiClient.put(`/api/rooms/${roomId}/status`, { status })
      message.success(`房间状态已更新`)
      setRefreshKey((k) => k + 1)
    } catch {
      message.error('操作失败')
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
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">📊 实时房态全景</h2>
        <Space>
          {Object.entries(stats).map(([key, value]) => (
            <Card size="small" key={key} styles={{ body: { padding: '8px 16px' } }}>
              <span className="text-lg font-bold" style={{ color: STATUS_COLORS[key] }}>{value}</span>
              <span className="text-xs text-gray-400 ml-2">{STATUS_LABELS[key]}</span>
            </Card>
          ))}
        </Space>
      </div>

      <div className="grid grid-cols-5 gap-3">
        {rooms.map((room) => (
          <Dropdown
            key={room.id}
            trigger={['contextMenu']}
            menu={{
              items: [
                ...(room.status === 'vacant'
                  ? [{ key: 'checkin', label: '🚪 快捷开房', onClick: () => setCheckInRoom(room.id) }]
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
              style={{ borderColor: STATUS_COLORS[room.status] || '#d9d9d9', borderWidth: 2 }}
              styles={{ body: { padding: '12px', textAlign: 'center' } }}
            >
              <div className="flex items-center justify-center gap-1 mb-1">
                <HomeOutlined style={{ color: STATUS_COLORS[room.status] }} />
                <strong className="text-lg">{room.room_number}</strong>
              </div>
              <div className="text-xs text-gray-400 mb-1">{ROOM_TYPE_LABELS[room.room_type] || room.room_type}</div>
              <Tag color={STATUS_COLORS[room.status]}>{STATUS_LABELS[room.status]}</Tag>
              <div className="text-base font-bold text-blue-500 mt-1">
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
