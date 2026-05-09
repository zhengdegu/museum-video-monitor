CREATE DATABASE IF NOT EXISTS museum_monitor DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE museum_monitor;

-- 库房
CREATE TABLE IF NOT EXISTS museum_storage_room (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '库房名称',
    code VARCHAR(50) UNIQUE COMMENT '库房编号',
    location VARCHAR(200) COMMENT '位置',
    description TEXT COMMENT '描述',
    status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 摄像头
CREATE TABLE IF NOT EXISTS museum_camera (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL COMMENT '所属库房',
    name VARCHAR(100) NOT NULL COMMENT '摄像头名称',
    rtsp_url VARCHAR(500) NOT NULL COMMENT 'RTSP拉流地址',
    segment_duration INT DEFAULT 10800 COMMENT '视频分段时长(秒)',
    status TINYINT DEFAULT 1 COMMENT '1在线 2离线 3拉流中',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

-- 原始视频
CREATE TABLE IF NOT EXISTS museum_source_video (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    camera_id BIGINT NOT NULL,
    source_type TINYINT DEFAULT 1 COMMENT '1自动拉取 2手动上传',
    local_path VARCHAR(500) COMMENT '本地存储路径',
    remote_url VARCHAR(500) COMMENT '线上存储URL',
    duration INT COMMENT '时长(秒)',
    file_size BIGINT COMMENT '文件大小(bytes)',
    start_time DATETIME COMMENT '视频开始时间',
    end_time DATETIME COMMENT '视频结束时间',
    analysis_status TINYINT DEFAULT 0 COMMENT '0待分析 1分析中 2已完成 3异常',
    upload_status TINYINT DEFAULT 0 COMMENT '0本地 1上传中 2已上传',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES museum_camera(id)
);

-- 人物视频段
CREATE TABLE IF NOT EXISTS museum_person_segment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_video_id BIGINT NOT NULL,
    start_time FLOAT NOT NULL COMMENT '开始时间(秒)',
    end_time FLOAT NOT NULL COMMENT '结束时间(秒)',
    person_count INT COMMENT '检测到的人数(偏向值)',
    local_path VARCHAR(500) COMMENT '切片本地路径',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_video_id) REFERENCES museum_source_video(id)
);

-- 动作片段(60s切片)
CREATE TABLE IF NOT EXISTS museum_source_video_segment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    person_segment_id BIGINT NOT NULL,
    segment_index INT NOT NULL COMMENT '片段序号',
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    frame_count INT COMMENT '抽帧数量',
    local_path VARCHAR(500),
    analysis_result JSON COMMENT '大模型分析结论',
    merged_summary TEXT COMMENT '增量合并后的摘要',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_segment_id) REFERENCES museum_person_segment(id)
);

-- 规则定义
CREATE TABLE IF NOT EXISTS museum_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '规则名称',
    code VARCHAR(50) UNIQUE COMMENT '规则编码',
    description TEXT COMMENT '规则描述',
    rule_type VARCHAR(50) COMMENT '规则类型',
    rule_config JSON COMMENT '规则配置参数',
    enabled TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 底层事件
CREATE TABLE IF NOT EXISTS museum_event (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_video_id BIGINT NOT NULL,
    person_segment_id BIGINT,
    camera_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    event_time DATETIME NOT NULL,
    event_type VARCHAR(50) COMMENT '事件类型',
    person_count INT,
    description TEXT COMMENT '事件描述',
    evidence_frames JSON COMMENT '证据截图路径列表',
    ai_conclusion TEXT COMMENT 'AI分析结论',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_video_id) REFERENCES museum_source_video(id),
    FOREIGN KEY (camera_id) REFERENCES museum_camera(id),
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

-- 规则命中快照
CREATE TABLE IF NOT EXISTS museum_rule_hit (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_id BIGINT NOT NULL,
    rule_id BIGINT NOT NULL,
    hit_time DATETIME NOT NULL,
    confidence FLOAT COMMENT '置信度',
    evidence_snapshot VARCHAR(500) COMMENT '证据截图',
    detail TEXT COMMENT '命中详情',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES museum_event(id),
    FOREIGN KEY (rule_id) REFERENCES museum_rule(id)
);

-- 库房会话级聚合事件
CREATE TABLE IF NOT EXISTS museum_event_aggregate (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL,
    camera_id BIGINT NOT NULL,
    session_start DATETIME NOT NULL,
    session_end DATETIME NOT NULL,
    total_events INT DEFAULT 0,
    rule_hits INT DEFAULT 0,
    summary TEXT COMMENT '聚合摘要',
    risk_level TINYINT DEFAULT 0 COMMENT '0正常 1低风险 2中风险 3高风险',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id),
    FOREIGN KEY (camera_id) REFERENCES museum_camera(id)
);

-- 藏品
CREATE TABLE IF NOT EXISTS museum_collection (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) UNIQUE,
    room_id BIGINT,
    category VARCHAR(50),
    description TEXT,
    image_url VARCHAR(500),
    status TINYINT DEFAULT 1 COMMENT '1在库 2出库 3展览中',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

-- 盘点记录
CREATE TABLE IF NOT EXISTS museum_inventory_check (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL COMMENT '库房ID',
    check_date DATE NOT NULL COMMENT '盘点日期',
    total_count INT DEFAULT 0 COMMENT '应盘数量',
    checked_count INT DEFAULT 0 COMMENT '已盘数量',
    matched_count INT DEFAULT 0 COMMENT '一致数量',
    mismatched_count INT DEFAULT 0 COMMENT '不一致数量',
    status TINYINT DEFAULT 0 COMMENT '0进行中 1已完成',
    operator VARCHAR(50) COMMENT '操作人',
    remark TEXT COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

-- 进出库记录
CREATE TABLE IF NOT EXISTS museum_collection_movement (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    collection_id BIGINT NOT NULL COMMENT '藏品ID',
    room_id BIGINT COMMENT '库房ID',
    movement_type TINYINT NOT NULL COMMENT '1入库 2出库 3移库',
    reason VARCHAR(200) COMMENT '原因',
    operator VARCHAR(50) COMMENT '操作人',
    moved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collection_id) REFERENCES museum_collection(id),
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

-- 分析任务队列
CREATE TABLE IF NOT EXISTS analysis_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    video_id BIGINT NOT NULL COMMENT '关联视频ID',
    camera_id BIGINT NOT NULL COMMENT '关联摄像头ID',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/running/completed/failed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    error_message TEXT NULL,
    retry_count INT DEFAULT 0 COMMENT '已重试次数',
    FOREIGN KEY (video_id) REFERENCES museum_source_video(id),
    FOREIGN KEY (camera_id) REFERENCES museum_camera(id)
);

-- ========== 索引 ==========

-- 事件表高频查询索引
CREATE INDEX idx_event_time ON museum_event(event_time);
CREATE INDEX idx_event_camera_id ON museum_event(camera_id);
CREATE INDEX idx_event_room_id ON museum_event(room_id);
CREATE INDEX idx_event_type ON museum_event(event_type);

-- 视频表分析状态索引
CREATE INDEX idx_video_analysis_status ON museum_source_video(analysis_status);
CREATE INDEX idx_video_camera_id ON museum_source_video(camera_id);

-- 规则命中索引
CREATE INDEX idx_rule_hit_event_id ON museum_rule_hit(event_id);
CREATE INDEX idx_rule_hit_rule_id ON museum_rule_hit(rule_id);

-- 摄像头按库房查询
CREATE INDEX idx_camera_room_id ON museum_camera(room_id);

-- 藏品按库房查询
CREATE INDEX idx_collection_room_id ON museum_collection(room_id);

-- 聚合事件索引
CREATE INDEX idx_aggregate_room_id ON museum_event_aggregate(room_id);
CREATE INDEX idx_aggregate_session_start ON museum_event_aggregate(session_start);

-- 人物片段按视频查询
CREATE INDEX idx_person_segment_video ON museum_person_segment(source_video_id);

-- 分析任务索引
CREATE INDEX idx_task_status ON analysis_task(status);
CREATE INDEX idx_task_video_id ON analysis_task(video_id);
CREATE INDEX idx_task_video_status ON analysis_task(video_id, status);

-- 合规报告
CREATE TABLE IF NOT EXISTS museum_report (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_type VARCHAR(20) NOT NULL COMMENT '报告类型: weekly/monthly/quarterly',
    start_date DATE NOT NULL COMMENT '统计开始日期',
    end_date DATE NOT NULL COMMENT '统计结束日期',
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
    data JSON COMMENT '结构化报告数据',
    html_path VARCHAR(500) COMMENT 'HTML报告文件路径',
    status VARCHAR(20) DEFAULT 'generating' COMMENT 'generating/completed/failed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_report_type ON museum_report(report_type);
CREATE INDEX idx_report_generated_at ON museum_report(generated_at);

-- 角色
CREATE TABLE IF NOT EXISTS sys_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(50) UNIQUE,
    permissions JSON COMMENT '权限列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    real_name VARCHAR(50),
    role_id BIGINT,
    status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES sys_role(id)
);

-- ========== 预置数据 ==========

-- 预置角色
INSERT INTO sys_role (name, code, permissions) VALUES
('超级管理员', 'admin', '["*"]'),
('普通用户', 'user', '["room:read","camera:read","video:read","event:read","collection:read","chat:use"]');

-- 预置管理员 (密码: admin123, bcrypt hash)
INSERT INTO sys_user (username, password_hash, real_name, role_id, status) VALUES
('admin', '$2b$12$LJ3m4ys3Lk0TSwHjfT0Abu8DfU5wvBfGFGnEqbPx5FqNVGFIVMPWe', '系统管理员', 1, 1);

-- API Key
CREATE TABLE IF NOT EXISTS sys_api_key (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '关联用户ID',
    name VARCHAR(100) NOT NULL COMMENT 'Key名称',
    key_hash VARCHAR(200) NOT NULL COMMENT 'Key的bcrypt哈希',
    key_prefix VARCHAR(8) NOT NULL COMMENT 'Key前8位明文用于展示',
    status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME NULL COMMENT '最后使用时间',
    FOREIGN KEY (user_id) REFERENCES sys_user(id)
);

CREATE INDEX idx_api_key_user_id ON sys_api_key(user_id);
CREATE INDEX idx_api_key_prefix ON sys_api_key(key_prefix);

-- Webhook 订阅
CREATE TABLE IF NOT EXISTS sys_webhook (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '关联用户ID',
    url VARCHAR(500) NOT NULL COMMENT 'Webhook回调URL',
    secret VARCHAR(200) NOT NULL COMMENT '签名密钥',
    event_types JSON COMMENT '订阅事件类型列表',
    status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES sys_user(id)
);

CREATE INDEX idx_webhook_user_id ON sys_webhook(user_id);

-- Webhook 投递日志
CREATE TABLE IF NOT EXISTS sys_webhook_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    webhook_id BIGINT NOT NULL,
    event_type VARCHAR(50) COMMENT '事件类型',
    payload JSON COMMENT '投递内容',
    response_code INT NULL COMMENT '响应状态码',
    attempts INT DEFAULT 0 COMMENT '尝试次数',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/success/failed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (webhook_id) REFERENCES sys_webhook(id)
);

CREATE INDEX idx_webhook_log_webhook_id ON sys_webhook_log(webhook_id);
CREATE INDEX idx_webhook_log_created_at ON sys_webhook_log(created_at);

-- ========== 预警系统相关表 ==========

-- 预警记录
CREATE TABLE IF NOT EXISTS museum_warning (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    camera_id BIGINT NOT NULL COMMENT '摄像头ID',
    room_id BIGINT NOT NULL COMMENT '库房ID',
    warning_type VARCHAR(50) NOT NULL COMMENT '预警类型: loiter/repeated_approach/acceleration/off_hours',
    risk_score INT DEFAULT 0 COMMENT '风险分数 0-100',
    person_track_id VARCHAR(100) COMMENT '人物轨迹追踪ID',
    trajectory_data JSON COMMENT '轨迹数据',
    description TEXT COMMENT '预警描述',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/resolved/dismissed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    FOREIGN KEY (camera_id) REFERENCES museum_camera(id),
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

CREATE INDEX idx_warning_camera_id ON museum_warning(camera_id);
CREATE INDEX idx_warning_room_id ON museum_warning(room_id);
CREATE INDEX idx_warning_type ON museum_warning(warning_type);
CREATE INDEX idx_warning_status ON museum_warning(status);
CREATE INDEX idx_warning_created_at ON museum_warning(created_at);
CREATE INDEX idx_warning_risk_score ON museum_warning(risk_score);

-- 预警规则配置
CREATE TABLE IF NOT EXISTS museum_warning_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_type VARCHAR(50) NOT NULL COMMENT '规则类型: loiter/repeated_approach/acceleration/off_hours',
    name VARCHAR(100) NOT NULL COMMENT '规则名称',
    config JSON COMMENT '规则配置',
    enabled TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 预置预警规则
INSERT INTO museum_warning_rule (rule_type, name, config, enabled) VALUES
('loiter', '藏品区域滞留预警', '{"threshold_seconds": 180, "risk_score": 60}', 1),
('repeated_approach', '反复接近同一位置预警', '{"min_count": 3, "radius": 50, "risk_score": 70}', 1),
('acceleration', '移动速度突增预警', '{"speed_increase_pct": 200, "risk_score": 50}', 1),
('off_hours', '非工作时间出现预警', '{"start_hour": 22, "end_hour": 6, "risk_score": 80}', 1);

-- ========== 推送渠道相关表 ==========

-- 推送渠道配置
CREATE TABLE IF NOT EXISTS sys_push_channel (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    channel_type VARCHAR(20) NOT NULL COMMENT '渠道类型: feishu/dingtalk/email/serverchan',
    name VARCHAR(100) NOT NULL COMMENT '渠道名称',
    config JSON COMMENT '渠道配置(JSON)',
    enabled TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    min_risk_level TINYINT DEFAULT 0 COMMENT '最低推送风险等级 0-3',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 推送日志
CREATE TABLE IF NOT EXISTS sys_push_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    channel_id BIGINT NOT NULL COMMENT '渠道ID',
    event_id BIGINT COMMENT '关联事件ID',
    status VARCHAR(20) NOT NULL COMMENT 'success/failed',
    response TEXT COMMENT '推送响应内容',
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES sys_push_channel(id)
);

CREATE INDEX idx_push_log_channel ON sys_push_log(channel_id);
CREATE INDEX idx_push_log_event ON sys_push_log(event_id);
CREATE INDEX idx_push_log_sent_at ON sys_push_log(sent_at);

-- museum_event 表新增反馈字段
ALTER TABLE museum_event ADD COLUMN feedback_status VARCHAR(20) DEFAULT NULL COMMENT '反馈状态: null/confirmed/dismissed';
ALTER TABLE museum_event ADD COLUMN feedback_at DATETIME DEFAULT NULL COMMENT '反馈时间';
ALTER TABLE museum_event ADD COLUMN feedback_by VARCHAR(50) DEFAULT NULL COMMENT '反馈人';

-- 预置6条核心安防规则
INSERT INTO museum_rule (name, code, description, rule_type, rule_config, enabled) VALUES
('进出库房人数限制', 'person_count_min_2', '进出库房的人数必须大于等于两人', 'person_count', '{"min_count": 2}', 1),
('着装要求', 'dress_uniform', '必须为统一工作服装，不允许携带背包等无关物品', 'dress', '{"require_uniform": true, "forbid_backpack": true}', 1),
('手持文物规范', 'dual_hand_hold', '手持文物时必须为双手持有，且另一人必须在旁监督', 'posture', '{"require_dual_hand": true, "require_supervisor": true}', 1),
('禁止危险行为', 'no_running', '禁止奔跑躲藏视角', 'behavior', '{"forbid_running": true, "forbid_jumping": true, "forbid_hiding": true}', 1),
('仅保留有人画面', 'person_frames_only', '只保留有人进出的画面，其余画面全部去掉', 'filter', '{"keep_person_only": true}', 1),
('自然语言事件检索', 'nlp_search', '支持自然语言沟通交流精准检索具体时间的具体事件', 'nlp', '{"enabled": true}', 1);

-- ========== AI 自动盘点相关表 ==========

-- AI 盘点任务
CREATE TABLE IF NOT EXISTS museum_ai_inventory_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL COMMENT '库房ID',
    trigger_type VARCHAR(20) NOT NULL COMMENT '触发类型: manual/scheduled',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed',
    started_at DATETIME NULL COMMENT '开始时间',
    completed_at DATETIME NULL COMMENT '完成时间',
    total_items INT DEFAULT 0 COMMENT '总藏品数',
    matched_items INT DEFAULT 0 COMMENT '在位数',
    missing_items INT DEFAULT 0 COMMENT '缺失数',
    uncertain_items INT DEFAULT 0 COMMENT '不确定数',
    error_message TEXT NULL COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

CREATE INDEX idx_ai_inv_task_room ON museum_ai_inventory_task(room_id);
CREATE INDEX idx_ai_inv_task_status ON museum_ai_inventory_task(status);
CREATE INDEX idx_ai_inv_task_created ON museum_ai_inventory_task(created_at);

-- AI 盘点结果（每件藏品）
CREATE TABLE IF NOT EXISTS museum_ai_inventory_result (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    collection_id BIGINT NOT NULL COMMENT '藏品ID',
    status VARCHAR(20) NOT NULL COMMENT '状态: present/missing/displaced/uncertain',
    confidence FLOAT DEFAULT 0.0 COMMENT '置信度 0-1',
    description TEXT NULL COMMENT '说明',
    frame_path VARCHAR(500) NULL COMMENT '截图路径',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES museum_ai_inventory_task(id),
    FOREIGN KEY (collection_id) REFERENCES museum_collection(id)
);

CREATE INDEX idx_ai_inv_result_task ON museum_ai_inventory_result(task_id);
CREATE INDEX idx_ai_inv_result_collection ON museum_ai_inventory_result(collection_id);
CREATE INDEX idx_ai_inv_result_status ON museum_ai_inventory_result(status);

-- AI 盘点定时配置
CREATE TABLE IF NOT EXISTS museum_ai_inventory_schedule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL COMMENT '库房ID',
    interval_hours INT DEFAULT 24 COMMENT '盘点间隔(小时)',
    enabled TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    last_run_at DATETIME NULL COMMENT '上次执行时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

CREATE INDEX idx_ai_inv_schedule_room ON museum_ai_inventory_schedule(room_id);

-- ========== 库房布局（数字孪生）==========

-- 库房布局
CREATE TABLE IF NOT EXISTS museum_room_layout (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL COMMENT '库房ID',
    width INT NOT NULL COMMENT '库房宽度(cm)',
    height INT NOT NULL COMMENT '库房高度(cm)',
    background_image VARCHAR(500) COMMENT '背景图片路径',
    layout_data JSON COMMENT '布局数据JSON',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_room_id (room_id),
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);

CREATE INDEX idx_room_layout_room_id ON museum_room_layout(room_id);

-- ========== 多馆管控相关表 ==========

-- 节点注册
CREATE TABLE IF NOT EXISTS sys_node (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '节点名称',
    location VARCHAR(200) COMMENT '节点位置',
    node_url VARCHAR(500) COMMENT '节点访问地址',
    api_key VARCHAR(200) NOT NULL COMMENT '节点通信API Key',
    status VARCHAR(20) DEFAULT 'offline' COMMENT '状态: online/offline/warning',
    version VARCHAR(50) COMMENT '节点版本',
    last_heartbeat_at DATETIME NULL COMMENT '最后心跳时间',
    system_info JSON COMMENT '系统信息',
    stats JSON COMMENT '运行统计',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_node_status ON sys_node(status);
CREATE INDEX idx_node_api_key ON sys_node(api_key);
