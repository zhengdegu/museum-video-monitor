import request from '../utils/request'

// Auth
export const login = (data: { username: string; password: string }) => request.post('/auth/login', data)
export const getMe = () => request.get('/auth/me')
export const getUsers = () => request.get('/auth/users')
export const createUser = (data: any) => request.post('/auth/users', data)
export const updateUser = (id: number, data: any) => request.put(`/auth/users/${id}`, data)
export const getRoles = () => request.get('/auth/roles')

// Rooms
export const getRooms = (params?: any) => request.get('/rooms', { params })
export const getRoom = (id: number) => request.get(`/rooms/${id}`)
export const createRoom = (data: any) => request.post('/rooms', data)
export const updateRoom = (id: number, data: any) => request.put(`/rooms/${id}`, data)
export const deleteRoom = (id: number) => request.delete(`/rooms/${id}`)

// Cameras
export const getCameras = (params?: any) => request.get('/cameras', { params })
export const getCamera = (id: number) => request.get(`/cameras/${id}`)
export const createCamera = (data: any) => request.post('/cameras', data)
export const updateCamera = (id: number, data: any) => request.put(`/cameras/${id}`, data)
export const deleteCamera = (id: number) => request.delete(`/cameras/${id}`)

// Videos
export const getVideos = (params?: any) => request.get('/videos', { params })
export const getVideo = (id: number) => request.get(`/videos/${id}`)
export const deleteVideo = (id: number) => request.delete(`/videos/${id}`)
export const triggerAnalyze = (id: number) => request.post(`/videos/${id}/analyze`)
export const uploadInit = (data: { camera_id: number; filename: string; file_size: number; total_chunks: number }) =>
  request.post('/videos/upload/init', data)
export const uploadChunk = (data: FormData) => request.post('/videos/upload/chunk', data)
export const uploadComplete = (data: FormData) => request.post('/videos/upload/complete', data)

// Events
export const getEvents = (params?: any) => request.get('/events', { params })
export const getEvent = (id: number) => request.get(`/events/${id}`)
export const getEventAggregates = (params?: any) => request.get('/events/aggregates', { params })
export const getEventRuleHits = (id: number) => request.get(`/events/${id}/rule-hits`)
export const getEventTrend = (days = 7) => request.get('/events/stats/trend', { params: { days } })
export const getRoomRisk = () => request.get('/events/stats/room-risk')
export const confirmEvent = (id: number) => request.post(`/events/${id}/confirm`)
export const dismissEvent = (id: number) => request.post(`/events/${id}/dismiss`)
export const getEventFeedback = (id: number) => request.get(`/events/${id}/feedback`)

// Push Channels
export const getPushChannels = () => request.get('/push-channels')
export const createPushChannel = (data: any) => request.post('/push-channels', data)
export const updatePushChannel = (id: number, data: any) => request.put(`/push-channels/${id}`, data)
export const deletePushChannel = (id: number) => request.delete(`/push-channels/${id}`)
export const testPushChannel = (id: number) => request.post(`/push-channels/${id}/test`)
export const getPushLogs = (params?: any) => request.get('/push-channels/logs', { params })

// Rules
export const getRules = (params?: any) => request.get('/rules', { params })
export const getRule = (id: number) => request.get(`/rules/${id}`)
export const createRule = (data: any) => request.post('/rules', data)
export const updateRule = (id: number, data: any) => request.put(`/rules/${id}`, data)
export const toggleRule = (id: number) => request.put(`/rules/${id}/toggle`)
export const deleteRule = (id: number) => request.delete(`/rules/${id}`)
export const getRuleHitStats = () => request.get('/rules/stats/hit-counts')

// Collections
export const getCollections = (params?: any) => request.get('/collections', { params })
export const getCollection = (id: number) => request.get(`/collections/${id}`)
export const createCollection = (data: any) => request.post('/collections', data)
export const updateCollection = (id: number, data: any) => request.put(`/collections/${id}`, data)
export const deleteCollection = (id: number) => request.delete(`/collections/${id}`)

// Chat
export const sendChat = (data: { message: string; session_id?: string }) => request.post('/chat', data)

// Inventory
export const getInventoryChecks = (params?: any) => request.get('/inventory/checks', { params })
export const createInventoryCheck = (data: any) => request.post('/inventory/checks', data)
export const updateInventoryCheck = (id: number, data: any) => request.put(`/inventory/checks/${id}`, data)
export const deleteInventoryCheck = (id: number) => request.delete(`/inventory/checks/${id}`)
export const exportInventoryCheck = (id: number) => `/api/v1/inventory/checks/${id}/export`
export const getMovements = (params?: any) => request.get('/inventory/movements', { params })
export const createMovement = (data: any) => request.post('/inventory/movements', data)

// AI Inventory
export const triggerAiInventory = (room_id: number) => request.post('/inventory-ai/trigger', null, { params: { room_id } })
export const getAiInventoryTasks = (params?: any) => request.get('/inventory-ai/tasks', { params })
export const getAiInventoryTaskDetail = (id: number) => request.get(`/inventory-ai/tasks/${id}`)
export const getAiInventoryTaskResults = (id: number, params?: any) => request.get(`/inventory-ai/tasks/${id}/results`, { params })
export const getAiInventorySchedule = () => request.get('/inventory-ai/schedule')
export const updateAiInventorySchedule = (params: { room_id: number; interval_hours: number; enabled: number }) =>
  request.put('/inventory-ai/schedule', null, { params })
export const getAiInventoryStats = (days?: number) => request.get('/inventory-ai/stats', { params: { days } })

// Video Segments (analysis detail)
export const getVideoSegments = (videoId: number) => request.get(`/videos/${videoId}/segments`)

// Reports
export const generateReport = (params: { start_date: string; end_date: string; report_type: string }) =>
  request.get('/reports/generate', { params })
export const getReportList = (params?: any) => request.get('/reports/list', { params })
export const getReportDownloadUrl = (id: number) => `/api/v1/reports/${id}/download`

// API Keys
export const getApiKeys = () => request.get('/api-keys')
export const createApiKey = (data: { name: string }) => request.post('/api-keys', data)
export const deleteApiKey = (id: number) => request.delete(`/api-keys/${id}`)
export const updateApiKey = (id: number, data: { status: number }) => request.patch(`/api-keys/${id}`, data)

// Webhooks
export const getWebhooks = () => request.get('/webhooks')
export const createWebhook = (data: { url: string; event_types: string[] }) => request.post('/webhooks', data)
export const updateWebhook = (id: number, data: any) => request.put(`/webhooks/${id}`, data)
export const deleteWebhook = (id: number) => request.delete(`/webhooks/${id}`)
export const getWebhookLogs = (id: number) => request.get(`/webhooks/${id}/logs`)
export const testWebhook = (id: number) => request.post(`/webhooks/${id}/test`)

// Warnings (预警中心)
export const getWarnings = (params?: any) => request.get('/warnings', { params })
export const getWarning = (id: number) => request.get(`/warnings/${id}`)
export const resolveWarning = (id: number) => request.post(`/warnings/${id}/resolve`)
export const dismissWarning = (id: number) => request.post(`/warnings/${id}/dismiss`)
export const getWarningStats = () => request.get('/warnings/stats')
export const getWarningRules = () => request.get('/warning-rules')
export const updateWarningRule = (id: number, data: any) => request.put(`/warning-rules/${id}`, data)

// Nodes (多馆管控)
export const getNodes = () => request.get('/nodes')
export const getNode = (id: number) => request.get(`/nodes/${id}`)
export const getNodesOverview = () => request.get('/nodes/overview')
export const createNode = (data: { name: string; location?: string; node_url?: string }) => request.post('/nodes', data)
export const deleteNode = (id: number) => request.delete(`/nodes/${id}`)
export const sendNodeCommand = (id: number, data: { command: string; params?: any }) => request.post(`/nodes/${id}/command`, data)

// Room Layout (数字孪生)
export const getRoomLayout = (roomId: number) => request.get(`/rooms/${roomId}/layout`)
export const saveRoomLayout = (roomId: number, data: any) => request.put(`/rooms/${roomId}/layout`, data)
export const getRoomHeatmap = (roomId: number, hours = 24) => request.get(`/rooms/${roomId}/heatmap`, { params: { hours } })
export const getRoomLiveStatus = (roomId: number) => request.get(`/rooms/${roomId}/live-status`)
