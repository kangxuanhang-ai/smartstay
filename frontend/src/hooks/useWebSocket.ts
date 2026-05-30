import { useEffect, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'

type EventHandler = (data: any) => void

const WS_URL = 'ws://localhost:8000/ws'

// 模块级单例：全局唯一连接
let globalWs: WebSocket | null = null
let globalHandlers: Map<string, Set<EventHandler>> = new Map()
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let currentToken: string | null = null

function ensureConnection(token: string) {
  if (globalWs && globalWs.readyState === WebSocket.OPEN && currentToken === token) return
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  if (globalWs) {
    globalWs.onclose = null
    globalWs.close()
  }
  currentToken = token
  const ws = new WebSocket(`${WS_URL}?token=${token}`)
  globalWs = ws

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      const event = msg.event
      const data = msg.data
      if (event && globalHandlers.has(event)) {
        for (const handler of globalHandlers.get(event)!) {
          handler(data)
        }
      }
    } catch {}
  }

  ws.onclose = () => {
    reconnectTimer = setTimeout(() => ensureConnection(token), 3000)
  }

  ws.onerror = () => {
    ws.close()
  }
}

export function useWebSocket() {
  const token = useAuthStore((s) => s.accessToken)

  const on = useCallback((event: string, handler: EventHandler) => {
    if (!globalHandlers.has(event)) {
      globalHandlers.set(event, new Set())
    }
    globalHandlers.get(event)!.add(handler)
    return () => {
      globalHandlers.get(event)?.delete(handler)
    }
  }, [])

  const off = useCallback((event: string, handler: EventHandler) => {
    globalHandlers.get(event)?.delete(handler)
  }, [])

  useEffect(() => {
    if (!token) return
    ensureConnection(token)
  }, [token])

  return { on, off }
}
