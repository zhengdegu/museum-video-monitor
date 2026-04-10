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
