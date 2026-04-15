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

-- 预置6条核心安防规则
INSERT INTO museum_rule (name, code, description, rule_type, rule_config, enabled) VALUES
('进出库房人数限制', 'person_count_min_2', '进出库房的人数必须大于等于两人', 'person_count', '{"min_count": 2}', 1),
('着装要求', 'dress_uniform', '必须为统一工作服装，不允许携带背包等无关物品', 'dress', '{"require_uniform": true, "forbid_backpack": true}', 1),
('手持文物规范', 'dual_hand_hold', '手持文物时必须为双手持有，且另一人必须在旁监督', 'posture', '{"require_dual_hand": true, "require_supervisor": true}', 1),
('禁止危险行为', 'no_running', '禁止奔跑躲藏视角', 'behavior', '{"forbid_running": true, "forbid_jumping": true, "forbid_hiding": true}', 1),
('仅保留有人画面', 'person_frames_only', '只保留有人进出的画面，其余画面全部去掉', 'filter', '{"keep_person_only": true}', 1),
('自然语言事件检索', 'nlp_search', '支持自然语言沟通交流精准检索具体时间的具体事件', 'nlp', '{"enabled": true}', 1);
