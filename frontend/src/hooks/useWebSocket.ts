import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'

type EventHandler = (data: any) => void

const WS_URL = 'ws://localhost:8000/ws'

export function useWebSocket() {
  const token = useAuthStore((s) => s.accessToken)
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map())
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const on = useCallback((event: string, handler: EventHandler) => {
    if (!handlersRef.current.has(event)) {
      handlersRef.current.set(event, new Set())
    }
    handlersRef.current.get(event)!.add(handler)
    return () => {
      handlersRef.current.get(event)?.delete(handler)
    }
  }, [])

  const off = useCallback((event: string, handler: EventHandler) => {
    handlersRef.current.get(event)?.delete(handler)
  }, [])

  useEffect(() => {
    if (!token) return

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}?token=${token}`)
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          const event = msg.event
          const data = msg.data
          if (event && handlersRef.current.has(event)) {
            for (const handler of handlersRef.current.get(event)!) {
              handler(data)
            }
          }
        } catch {}
      }

      ws.onclose = () => {
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [token])

  return { on, off }
}
