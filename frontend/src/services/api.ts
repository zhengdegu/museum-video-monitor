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

// Video Segments (analysis detail)
export const getVideoSegments = (videoId: number) => request.get(`/videos/${videoId}/segments`)
