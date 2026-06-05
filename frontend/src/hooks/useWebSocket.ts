import { useEffect, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'

type EventHandler = (data: any) => void

const WS_URL = import.meta.env.VITE_WS_BASE_URL
  ? `${import.meta.env.VITE_WS_BASE_URL}/ws`
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`

// 模块级单例：全局唯一连接
let globalWs: WebSocket | null = null
let globalHandlers: Map<string, Set<EventHandler>> = new Map()
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let heartbeatTimer: ReturnType<typeof setTimeout> | null = null
let currentToken: string | null = null

function resetHeartbeat() {
  if (heartbeatTimer) clearTimeout(heartbeatTimer)
  heartbeatTimer = setTimeout(() => {
    // No message received in 60s — connection is dead, force reconnect
    if (globalWs) {
      globalWs.onclose = null
      globalWs.close()
      globalWs = null
    }
    if (currentToken) ensureConnection(currentToken)
  }, 60000)
}

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
    resetHeartbeat()
    try {
      const msg = JSON.parse(e.data)
      const event = msg.event
      const data = msg.data
      if (event && globalHandlers.has(event)) {
        for (const handler of globalHandlers.get(event)!) {
          handler(data)
        }
      }
    } catch {
      console.warn('WebSocket message parse error')
    }
  }

  ws.onopen = () => {
    resetHeartbeat()
  }

  ws.onclose = () => {
    if (heartbeatTimer) { clearTimeout(heartbeatTimer); heartbeatTimer = null }
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
