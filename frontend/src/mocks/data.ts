// Mock data for museum video monitor frontend

export const mockToken = 'mock-jwt-token-genesis-2025'

export const mockUser = { id: 1, username: 'admin', real_name: '系统管理员', role_id: 1 }

export const mockRooms = {
  items: [
    { id: 1, name: 'A1 青铜器库', location: '主楼1层', area: 120, camera_count: 6, temperature: 22.5, humidity: 55, status: 1, risk_level: 0 },
    { id: 2, name: 'A2 书画库', location: '主楼2层', area: 180, camera_count: 8, temperature: 28.5, humidity: 72, status: 1, risk_level: 2 },
    { id: 3, name: 'B1 陶瓷库', location: '副楼1层', area: 95, camera_count: 5, temperature: 21.8, humidity: 50, status: 1, risk_level: 0 },
    { id: 4, name: 'B2 玉器库', location: '副楼2层', area: 110, camera_count: 7, temperature: 23.1, humidity: 58, status: 1, risk_level: 3 },
    { id: 5, name: 'C1 杂项库', location: '西馆1层', area: 75, camera_count: 4, temperature: 22.0, humidity: 52, status: 1, risk_level: 0 },
    { id: 6, name: 'C2 临展库', location: '西馆2层', area: 200, camera_count: 6, temperature: null, humidity: null, status: 0, risk_level: 0 },
  ],
  total: 6
}

export const mockCameras = {
  items: [
    { id: 1, name: 'CAM-A1-01', room_id: 1, room_name: 'A1 青铜器库', location: '入口', rtsp_url: 'rtsp://192.168.1.101/stream1', status: 1, resolution: '1920x1080', fps: 30 },
    { id: 2, name: 'CAM-A1-02', room_id: 1, room_name: 'A1 青铜器库', location: '主区域', rtsp_url: 'rtsp://192.168.1.102/stream1', status: 1, resolution: '2560x1440', fps: 25 },
    { id: 3, name: 'CAM-A2-01', room_id: 2, room_name: 'A2 书画库', location: '入口', rtsp_url: 'rtsp://192.168.1.103/stream1', status: 0, resolution: '1920x1080', fps: 30 },
    { id: 4, name: 'CAM-A2-02', room_id: 2, room_name: 'A2 书画库', location: '展柜区', rtsp_url: 'rtsp://192.168.1.104/stream1', status: 1, resolution: '1920x1080', fps: 30 },
    { id: 5, name: 'CAM-B1-01', room_id: 3, room_name: 'B1 陶瓷库', location: '全景', rtsp_url: 'rtsp://192.168.1.105/stream1', status: 1, resolution: '3840x2160', fps: 20 },
    { id: 6, name: 'CAM-B2-01', room_id: 4, room_name: 'B2 玉器库', location: '入口', rtsp_url: 'rtsp://192.168.1.106/stream1', status: 1, resolution: '1920x1080', fps: 30 },
    { id: 7, name: 'CAM-B2-02', room_id: 4, room_name: 'B2 玉器库', location: '展柜', rtsp_url: 'rtsp://192.168.1.107/stream1', status: 0, resolution: '1920x1080', fps: 30 },
    { id: 8, name: 'CAM-C1-01', room_id: 5, room_name: 'C1 杂项库', location: '全景', rtsp_url: 'rtsp://192.168.1.108/stream1', status: 1, resolution: '1920x1080', fps: 30 },
  ],
  total: 52
}

export const mockVideos = {
  items: [
    { id: 1, filename: 'VID_20250509_0942.mp4', camera_id: 6, camera_name: 'CAM-B2-01', room_name: 'B2玉器库', duration: 300, recorded_at: '2025-05-09 09:42:00', status: 'analyzed', result: 'abnormal' },
    { id: 2, filename: 'VID_20250509_1015.mp4', camera_id: 4, camera_name: 'CAM-A2-02', room_name: 'A2书画库', duration: 300, recorded_at: '2025-05-09 10:15:00', status: 'analyzing', result: null },
    { id: 3, filename: 'VID_20250509_1100.mp4', camera_id: 1, camera_name: 'CAM-A1-01', room_name: 'A1青铜器库', duration: 300, recorded_at: '2025-05-09 11:00:00', status: 'analyzed', result: 'normal' },
    { id: 4, filename: 'VID_20250509_1130.mp4', camera_id: 5, camera_name: 'CAM-B1-01', room_name: 'B1陶瓷库', duration: 300, recorded_at: '2025-05-09 11:300', status: 'pending', result: null },
    { id: 5, filename: 'VID_20250509_1200.mp4', camera_id: 2, camera_name: 'CAM-A1-02', room_name: 'A1青铜器库', duration: 300, recorded_at: '2025-05-09 12:00:00', status: 'analyzed', result: 'normal' },
    { id: 6, filename: 'VID_20250509_1230.mp4', camera_id: 8, camera_name: 'CAM-C1-01', room_name: 'C1杂项库', duration: 300, recorded_at: '2025-05-09 12:30:00', status: 'analyzing', result: null },
  ],
  total: 86
}

export const mockEvents = {
  items: [
    { id: 1, created_at: '2025-05-09 09:42:00', room_name: 'B2 玉器库', camera_name: 'CAM-B2-01', event_type: '未授权人员', description: '检测到非登记人员进入B2玉器库', risk_level: 3, status: 'pending', ai_conclusion: '置信度94.2%，建议立即核查' },
    { id: 2, created_at: '2025-05-09 14:15:00', room_name: 'A2 书画库', camera_name: 'CAM-A2-02', event_type: '温湿度异常', description: '温度28.5C超阈值26C', risk_level: 2, status: 'resolved', ai_conclusion: '空调系统异常，已自动通知维保' },
    { id: 3, created_at: '2025-05-09 16:30:00', room_name: 'C1 杂项库', camera_name: 'CAM-C1-01', event_type: '人员滞留', description: '同一人员停留42分钟', risk_level: 1, status: 'pending', ai_conclusion: '可能为正常盘点作业' },
    { id: 4, created_at: '2025-05-08 22:10:00', room_name: 'A1 青铜器库', camera_name: 'CAM-A1-01', event_type: '异常移动', description: '夜间检测到物体位移', risk_level: 2, status: 'resolved', ai_conclusion: '经核查为保洁人员正常作业' },
    { id: 5, created_at: '2025-05-08 08:05:00', room_name: 'B1 陶瓷库', camera_name: 'CAM-B1-01', event_type: '着装违规', description: '未佩戴防护手套', risk_level: 1, status: 'resolved', ai_conclusion: '已通知当事人整改' },
    { id: 6, created_at: '2025-05-07 19:30:00', room_name: 'B2 玉器库', camera_name: 'CAM-B2-02', event_type: '异常行为', description: '检测到快速奔跑行为', risk_level: 3, status: 'resolved', ai_conclusion: '安保人员已到场处理' },
  ],
  total: 38
}

export const mockEventTrend = [
  { date: '2025-05-03', count: 3 },
  { date: '2025-05-04', count: 5 },
  { date: '2025-05-05', count: 2 },
  { date: '2025-05-06', count: 8 },
  { date: '2025-05-07', count: 4 },
  { date: '2025-05-08', count: 9 },
  { date: '2025-05-09', count: 7 },
]

export const mockRoomRisk = [
  { room_id: 1, room_name: 'A1 青铜器库', risk_level: 0 },
  { room_id: 2, room_name: 'A2 书画库', risk_level: 2 },
  { room_id: 3, room_name: 'B1 陶瓷库', risk_level: 0 },
  { room_id: 4, room_name: 'B2 玉器库', risk_level: 3 },
  { room_id: 5, room_name: 'C1 杂项库', risk_level: 0 },
]

export const mockWarnings = {
  items: [
    { id: 1, created_at: '2025-05-09 09:42:00', room_name: 'B2 玉器库', level: 'high', title: '未授权人员进入', description: '检测到非登记人员进入B2玉器库，已自动触发门禁锁定', status: 'active' },
    { id: 2, created_at: '2025-05-09 14:15:00', room_name: 'A2 书画库', level: 'medium', title: '温湿度超标', description: '当前温度28.5C(阈值26C)，湿度72%(阈值65%)', status: 'active' },
    { id: 3, created_at: '2025-05-09 16:30:00', room_name: 'C1 杂项库', level: 'low', title: '人员滞留超时', description: '工作人员张三停留已超过42分钟', status: 'active' },
  ],
  total: 3
}

export const mockWarningStats = { active_count: 3, today_count: 5, resolved_count: 12, false_alarm_rate: 8.5 }

export const mockRules = {
  items: [
    { id: 1, name: '未授权人员检测', description: '检测非授权人员进入库房区域', risk_level: 3, enabled: true, trigger_count: 12 },
    { id: 2, name: '温湿度异常监测', description: '温度>26C或湿度>65%持续10分钟', risk_level: 2, enabled: true, trigger_count: 8 },
    { id: 3, name: '人员滞留检测', description: '同一人员停留超过30分钟', risk_level: 1, enabled: true, trigger_count: 25 },
    { id: 4, name: '着装规范检测', description: '检测是否佩戴手套、穿着工作服', risk_level: 1, enabled: false, trigger_count: 0 },
    { id: 5, name: '异常行为检测', description: '检测奔跑、攀爬、打斗等行为', risk_level: 3, enabled: true, trigger_count: 3 },
    { id: 6, name: '夜间活动检测', description: '22:00-06:00检测到人员活动即报警', risk_level: 2, enabled: true, trigger_count: 6 },
  ],
  total: 6
}

export const mockCollections = {
  items: [
    { id: 1, name: '商代后母戊鼎', category: '青铜器', room_name: 'A1青铜器库', code: 'BZ-001', level: '一级' },
    { id: 2, name: '清明上河图(摹本)', category: '书画', room_name: 'A2书画库', code: 'SH-012', level: '二级' },
    { id: 3, name: '宋代汝窑天青釉瓶', category: '陶瓷', room_name: 'B1陶瓷库', code: 'TC-008', level: '一级' },
    { id: 4, name: '战国白玉龙纹璧', category: '玉器', room_name: 'B2玉器库', code: 'YQ-003', level: '一级' },
    { id: 5, name: '汉代铜印章', category: '杂项', room_name: 'C1杂项库', code: 'ZX-015', level: '三级' },
    { id: 6, name: '越王勾践剑(复制品)', category: '青铜器', room_name: 'A1青铜器库', code: 'BZ-022', level: '复制品' },
    { id: 7, name: '明代宣德炉', category: '青铜器', room_name: 'A1青铜器库', code: 'BZ-035', level: '二级' },
    { id: 8, name: '元代青花瓷碗', category: '陶瓷', room_name: 'B1陶瓷库', code: 'TC-019', level: '二级' },
    { id: 9, name: '汉代玉佩', category: '玉器', room_name: 'B2玉器库', code: 'YQ-011', level: '三级' },
  ],
  total: 128
}

export const mockInventoryChecks = {
  items: [
    { id: 1, created_at: '2025-05-09 08:30:00', collection_name: '商代后母戊鼎', code: 'BZ-001', type: 'out', room_name: 'A1', operator: '张三', approver: '李四', status: 'completed' },
    { id: 2, created_at: '2025-05-09 10:00:00', collection_name: '宋代汝窑天青釉瓶', code: 'TC-008', type: 'in', room_name: 'B1', operator: '李四', approver: '王五', status: 'completed' },
    { id: 3, created_at: '2025-05-09 14:00:00', collection_name: '清明上河图(摹本)', code: 'SH-012', type: 'out', room_name: 'A2', operator: '王五', approver: null, status: 'pending' },
    { id: 4, created_at: '2025-05-09 15:20:00', collection_name: '汉代玉佩', code: 'YQ-011', type: 'out', room_name: 'B2', operator: '张三', approver: null, status: 'pending' },
    { id: 5, created_at: '2025-05-08 16:30:00', collection_name: '汉代铜印章', code: 'ZX-015', type: 'in', room_name: 'C1', operator: '赵六', approver: '张三', status: 'completed' },
  ],
  total: 42
}

export const mockUsers = [
  { id: 1, username: 'admin', real_name: '系统管理员', role_id: 1, role_name: '超级管理员', department: '信息中心', status: 1, last_login: '2025-05-09 08:00:00' },
  { id: 2, username: 'zhangsan', real_name: '张三', role_id: 2, role_name: '库房管理员', department: '藏品部', status: 1, last_login: '2025-05-09 08:30:00' },
  { id: 3, username: 'lisi', real_name: '李四', role_id: 2, role_name: '库房管理员', department: '藏品部', status: 0, last_login: '2025-05-08 17:30:00' },
  { id: 4, username: 'wangwu', real_name: '王五', role_id: 3, role_name: '安保主管', department: '安保部', status: 1, last_login: '2025-05-09 07:00:00' },
  { id: 5, username: 'zhaoliu', real_name: '赵六', role_id: 4, role_name: '安保人员', department: '安保部', status: 0, last_login: '2025-05-08 22:00:00' },
]

export const mockPushChannels = [
  { id: 1, name: '飞书机器人', type: 'feishu', target: '安全预警群', webhook_url: 'https://open.feishu.cn/...xxx', level: 'medium', enabled: true, today_count: 3 },
  { id: 2, name: '钉钉群', type: 'dingtalk', target: '馆长办公群', webhook_url: 'https://oapi.dingtalk.com/...yyy', level: 'high', enabled: true, today_count: 1 },
  { id: 3, name: '邮件通知', type: 'email', target: 'admin@museum.cn', webhook_url: 'smtp://smtp.museum.cn', level: 'all', enabled: false, today_count: 0 },
]

export const mockApiKeys = [
  { id: 1, name: '生产环境', key_prefix: 'sk-prod-****7f3a', permissions: 'full', rate_limit: '1000/min', last_used: '刚刚', status: 1 },
  { id: 2, name: '测试环境', key_prefix: 'sk-test-****2b1c', permissions: 'read', rate_limit: '100/min', last_used: '2小时前', status: 1 },
  { id: 3, name: '飞书集成', key_prefix: 'sk-fs-****9e4d', permissions: 'events', rate_limit: '500/min', last_used: '30分钟前', status: 1 },
]

export const mockWebhooks = [
  { id: 1, name: '安防系统同步', url: 'https://security.museum.cn/hook', event_types: ['high_risk'], success_rate: 100, last_triggered: '09:42', enabled: true },
  { id: 2, name: 'OA 系统通知', url: 'https://oa.museum.cn/api/notify', event_types: ['medium_risk', 'high_risk'], success_rate: 98.5, last_triggered: '14:15', enabled: true },
  { id: 3, name: '数据分析平台', url: 'https://bi.museum.cn/ingest', event_types: ['all'], success_rate: 92.3, last_triggered: '16:30', enabled: true },
]

export const mockNodes = [
  { id: 1, name: '主馆 - 中心博物馆', location: '市中心文化路1号', status: 'online', rooms: 6, cameras: 52, today_events: 7, score: 78 },
  { id: 2, name: '分馆 - 东区展览馆', location: '东区科技园路88号', status: 'online', rooms: 3, cameras: 24, today_events: 2, score: 91 },
  { id: 3, name: '分馆 - 西区文物库', location: '西区保护路12号', status: 'offline', rooms: 4, cameras: 18, today_events: 0, score: 0 },
]

export const mockReports = [
  { id: 1, name: '2025年第19周安全合规报告', created_at: '2025-05-09', type: 'weekly', score: 78 },
  { id: 2, name: '2025年第18周安全合规报告', created_at: '2025-05-02', type: 'weekly', score: 83 },
  { id: 3, name: '2025年4月安全合规报告', created_at: '2025-05-01', type: 'monthly', score: 81 },
  { id: 4, name: '2025年Q1安全合规报告', created_at: '2025-04-01', type: 'quarterly', score: 85 },
]

export const mockAiInventoryTasks = [
  { id: 1, room_name: 'A1 青铜器库', started_at: '2025-05-07 09:00:00', expected: 45, actual: 45, match_rate: 100, anomalies: 0, status: 'passed' },
  { id: 2, room_name: 'A2 书画库', started_at: '2025-05-07 10:30:00', expected: 62, actual: 62, match_rate: 100, anomalies: 0, status: 'passed' },
  { id: 3, room_name: 'B1 陶瓷库', started_at: '2025-05-07 13:00:00', expected: 38, actual: 38, match_rate: 100, anomalies: 0, status: 'passed' },
  { id: 4, room_name: 'B2 玉器库', started_at: '2025-05-07 14:30:00', expected: 51, actual: 50, match_rate: 98, anomalies: 1, status: 'anomaly' },
  { id: 5, room_name: 'C1 杂项库', started_at: '2025-05-07 16:00:00', expected: 29, actual: 29, match_rate: 100, anomalies: 0, status: 'passed' },
]

export const mockChatResponses = [
  '根据系统记录，当前所有库房运行状态正常。最近一次巡检时间为今日08:00，未发现异常。',
  '当前系统整体安全评分为78分，主要风险点集中在B2玉器库（门禁漏洞）和A2书画库（温控异常）。',
  '过去7天共发生38起事件，其中高风险5起、中风险12起、低风险21起。整体趋势较上周上升15%。',
  '所有摄像头中有48台在线、4台离线。离线摄像头：CAM-A2-01（信号中断）、CAM-B2-02（维护中）。',
  '最新盘点结果显示藏品匹配率99.2%，B2玉器库有1件藏品位置异常（YQ-007 玉琮）。',
]
