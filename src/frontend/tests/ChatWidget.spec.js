import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import ChatWidget from '../components/ChatWidget.vue'

describe('ChatWidget.vue', () => {
  let wrapper
  const mockWebSocket = {
    send: vi.fn(),
    close: vi.fn()
  }

  global.WebSocket = vi.fn(() => mockWebSocket)

  beforeEach(() => {
    wrapper = mount(ChatWidget, {
      props: {
        websocket_url: 'ws://test.url',
        disabled: false
      }
    })
  })

  it('initializes with correct default state', () => {
    expect(wrapper.vm.messages).toEqual([])
    expect(wrapper.vm.userInput).toBe('')
    expect(wrapper.vm.conversationCompleted).toBe(false)
    expect(wrapper.vm.connectionState).toBe('disconnected')
  })

  it('connects to WebSocket on mount', () => {
    expect(global.WebSocket).toHaveBeenCalledWith('ws://test.url')
  })

  it('displays user messages correctly', async () => {
    await wrapper.setData({
      connectionState: 'connected',
      messages: [
        { role: 'user', content: 'Hello' },
        { role: 'agent', content: 'Hi there!' }
      ]
    })

    const messages = wrapper.findAll('.message')
    expect(messages).toHaveLength(2)
    expect(messages[0].text()).toContain('Hello')
    expect(messages[1].text()).toContain('Hi there!')
  })

  it('handles sending messages', async () => {
    await wrapper.setData({
      connectionState: 'connected',
      userInput: 'Test message'
    })

    await wrapper.find('button.send-button').trigger('click')

    expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify({ content: 'Test message' }))
    expect(wrapper.vm.userInput).toBe('')
  })

  it('disables input when conversation is completed', async () => {
    await wrapper.setData({ conversationCompleted: true })

    const input = wrapper.find('textarea')
    const button = wrapper.find('button')

    expect(input.attributes('disabled')).toBeDefined()
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('handles WebSocket messages correctly', async () => {
    const mockMessage = {
      type: 'agent_response',
      content: 'Test response',
      data: { is_complete: false }
    }

    await wrapper.vm.handleWebSocketMessage(mockMessage)

    expect(wrapper.vm.messages).toContainEqual({
      role: 'agent',
      content: 'Test response',
      timestamp: expect.any(Date)
    })
  })

  it('handles conversation completion', async () => {
    const mockCompletionMessage = {
      type: 'agent_response',
      content: 'Goodbye',
      data: { is_complete: true, summary: { responses: [] } }
    }

    const emitSpy = vi.spyOn(wrapper.vm, '$emit')
    await wrapper.vm.handleWebSocketMessage(mockCompletionMessage)

    expect(wrapper.vm.conversationCompleted).toBe(true)
    expect(emitSpy).toHaveBeenCalledWith('conversation-complete', { responses: [] })
  })

  it('handles reconnection attempts', async () => {
    await wrapper.vm.attemptReconnect()

    expect(wrapper.vm.reconnectAttempts).toBe(1)
    expect(wrapper.vm.connectionState).toBe('reconnecting')
  })

  it('handles UI configuration messages', async () => {
    const mockConfig = {
      type: 'ui_config',
      data: {
        avatar: {
          show: true,
          url: 'test.url'
        }
      }
    }

    const emitSpy = vi.spyOn(wrapper.vm, '$emit')
    await wrapper.vm.handleWebSocketMessage(mockConfig)

    expect(emitSpy).toHaveBeenCalledWith('ui-config', mockConfig)
  })
}) 