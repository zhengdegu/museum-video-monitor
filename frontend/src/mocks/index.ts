import axios from 'axios'
import {
  mockToken, mockUser, mockRooms, mockCameras, mockVideos, mockEvents,
  mockEventTrend, mockRoomRisk, mockWarnings, mockWarningStats, mockRules,
  mockCollections, mockInventoryChecks, mockUsers, mockPushChannels,
  mockApiKeys, mockWebhooks, mockNodes, mockReports, mockAiInventoryTasks,
  mockChatResponses
} from './data'

// Set a mock token so the app thinks we're logged in
if (!localStorage.getItem('token')) {
  localStorage.setItem('token', mockToken)
}

// Intercept all axios errors (which happen because there's no backend)
// and return mock data instead
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const config = error.config
    if (!config) return Promise.reject(error)

    const url = config.url || ''
    const method = (config.method || 'get').toLowerCase()
    let body: any = {}
    try { body = config.data ? JSON.parse(config.data) : {} } catch(e) { body = {} }

    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ data: routeMock(url, method, body), status: 200, statusText: 'OK', headers: {}, config })
      }, 200 + Math.random() * 300)
    })
  }
)

function routeMock(url: string, method: string, body?: any): any {
  // Auth
  if (url.includes('/auth/login')) {
    return { code: 200, data: { access_token: mockToken, user: mockUser } }
  }
  if (url.includes('/auth/me')) {
    return { code: 200, data: mockUser }
  }
  if (url.includes('/auth/users') && method === 'get') {
    return { code: 200, data: mockUsers }
  }
  if (url.includes('/auth/roles')) {
    return { code: 200, data: [{ id: 1, name: '超级管理员' }, { id: 2, name: '库房管理员' }, { id: 3, name: '安保主管' }, { id: 4, name: '安保人员' }] }
  }

  // Rooms
  if (url.match(/\/rooms\/\d+\/layout/)) return { code: 200, data: { zones: [] } }
  if (url.match(/\/rooms\/\d+\/heatmap/)) return { code: 200, data: [] }
  if (url.match(/\/rooms\/\d+\/live-status/)) return { code: 200, data: { online_cameras: 4, people_count: 2 } }
  if (url.match(/\/rooms\/\d+/) && method === 'get') return { code: 200, data: mockRooms.items[0] }
  if (url.includes('/rooms') && method === 'get') return { code: 200, data: mockRooms }
  if (url.includes('/rooms') && (method === 'post' || method === 'put')) return { code: 200, data: { id: 7 } }

  // Cameras
  if (url.includes('/cameras') && method === 'get') return { code: 200, data: mockCameras }
  if (url.includes('/cameras') && method === 'post') return { code: 200, data: { id: 9 } }

  // Videos
  if (url.includes('/videos') && url.includes('/segments')) return { code: 200, data: [] }
  if (url.includes('/analyze')) return { code: 200, data: { task_id: 1 } }
  if (url.includes('/videos') && method === 'get') return { code: 200, data: mockVideos }

  // Events
  if (url.includes('/events/stats/trend')) return { code: 200, data: mockEventTrend }
  if (url.includes('/events/stats/room-risk')) return { code: 200, data: mockRoomRisk }
  if (url.includes('/events/aggregates')) return { code: 200, data: { items: mockEvents.items.filter((e: any) => e.risk_level === 3), total: 5 } }
  if (url.includes('/events') && url.includes('/feedback')) return { code: 200, data: [] }
  if (url.includes('/events') && url.includes('/rule-hits')) return { code: 200, data: [] }
  if (url.includes('/confirm') || url.includes('/dismiss')) return { code: 200, data: {} }
  if (url.includes('/events') && method === 'get') return { code: 200, data: mockEvents }

  // Warnings
  if (url.includes('/warnings/stats')) return { code: 200, data: mockWarningStats }
  if (url.includes('/warning-rules')) return { code: 200, data: mockRules.items }
  if (url.includes('/warnings') && url.includes('/resolve')) return { code: 200, data: {} }
  if (url.includes('/warnings') && method === 'get') return { code: 200, data: mockWarnings }

  // Rules
  if (url.includes('/rules/stats')) return { code: 200, data: mockRules.items.map((r: any) => ({ rule_id: r.id, hit_count: r.trigger_count })) }
  if (url.includes('/toggle')) return { code: 200, data: {} }
  if (url.includes('/rules') && method === 'get') return { code: 200, data: mockRules }

  // Collections
  if (url.includes('/collections') && method === 'get') return { code: 200, data: mockCollections }

  // Chat
  if (url.includes('/chat') && method === 'post') {
    const resp = mockChatResponses[Math.floor(Math.random() * mockChatResponses.length)]
    return { code: 200, data: { reply: resp, session_id: 'mock-session-1' } }
  }

  // Inventory
  if (url.includes('/inventory/movements') || url.includes('/inventory/checks')) {
    if (method === 'get') return { code: 200, data: mockInventoryChecks }
    return { code: 200, data: { id: 6 } }
  }

  // AI Inventory
  if (url.includes('/inventory-ai/stats')) return { code: 200, data: { total_tasks: 5, match_rate: 99.2, coverage: '6/6' } }
  if (url.includes('/inventory-ai/tasks')) return { code: 200, data: { items: mockAiInventoryTasks, total: 5 } }
  if (url.includes('/inventory-ai/trigger')) return { code: 200, data: { task_id: 6 } }
  if (url.includes('/inventory-ai/schedule')) return { code: 200, data: { room_id: 1, interval_hours: 24, enabled: 1 } }

  // Reports
  if (url.includes('/reports/generate')) return { code: 200, data: { id: 5, content: 'AI生成的合规报告...' } }
  if (url.includes('/reports')) return { code: 200, data: { items: mockReports, total: 4 } }

  // Push Channels
  if (url.includes('/push-channels') && url.includes('/logs')) return { code: 200, data: { items: [], total: 0 } }
  if (url.includes('/push-channels') && url.includes('/test')) return { code: 200, data: { success: true } }
  if (url.includes('/push-channels') && method === 'get') return { code: 200, data: mockPushChannels }

  // API Keys
  if (url.includes('/api-keys') && method === 'get') return { code: 200, data: mockApiKeys }
  if (url.includes('/api-keys') && method === 'post') return { code: 200, data: { id: 4, key: 'sk-new-xxxx1234' } }

  // Webhooks
  if (url.includes('/webhooks') && url.includes('/logs')) return { code: 200, data: [] }
  if (url.includes('/webhooks') && url.includes('/test')) return { code: 200, data: { success: true } }
  if (url.includes('/webhooks') && method === 'get') return { code: 200, data: mockWebhooks }
  if (url.includes('/webhooks') && method === 'post') return { code: 200, data: { id: 4 } }

  // Nodes
  if (url.includes('/nodes/overview')) return { code: 200, data: { total: 3, online: 2, offline: 1 } }
  if (url.includes('/nodes') && url.includes('/command')) return { code: 200, data: { success: true } }
  if (url.includes('/nodes') && method === 'get') return { code: 200, data: mockNodes }

  // Agent
  if (url.includes('/agent/health')) return { code: 200, data: { status: 'healthy', timestamp: new Date().toISOString(), rooms: { active: 5, total: 6 }, cameras: { online: 48, total: 52 }, analyzing_videos: 2 } }

  // Default
  return { code: 200, data: {} }
}

console.log('[Mock] API interceptor active - running without backend')
