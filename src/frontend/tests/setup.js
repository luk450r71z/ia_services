import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Mock WebSocket
global.WebSocket = class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = WebSocket.CONNECTING
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      this.onopen && this.onopen()
    }, 0)
  }

  send(data) {}
  close() {}

  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
}

// Mock console methods to avoid noise in tests
console.log = vi.fn()
console.error = vi.fn()
console.warn = vi.fn()

// Configure Vue Test Utils
config.global.mocks = {
  $config: {
    environment: 'test'
  }
} 