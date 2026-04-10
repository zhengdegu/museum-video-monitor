# 博物馆视频智能监控分析平台 — 技术设计

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   前端 (React)                       │
│  动态路由 + RBAC │ Ant Design │ flv.js 视频播放      │
├─────────────────────────────────────────────────────┤
│                  后端 (FastAPI)                       │
│  RESTful API │ WebSocket │ 异步任务调度               │
├──────────┬──────────┬──────────┬────────────────────┤
│ 视觉分析  │ NLP 引擎  │ 规则引擎  │ 存储服务          │
│ YOLO11   │ Qwen3-32B│ 裁判模型  │ MySQL + Milvus    │
│ YOLO-Pose│ Qwen3.5  │          │ MinIO + 本地FS     │
│ByteTracker│ vLLM    │          │                    │
└──────────┴──────────┴──────────┴────────────────────┘
```

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | React 18 + TypeScript + Ant Design | 动态路由 + RBAC |
| 后端 | FastAPI (Python 3.11+) | 异步框架，高性能 |
| 目标检测 | YOLO 11m + 自定义数据集(~1000张) | ultralytics |
| 姿态检测 | YOLO-Pose + ByteTracker | 行为分析 |
| 文本推理 | Qwen3-32B + vLLM | 本地部署 |
| 多模态分析 | Qwen3.5-35B-A3B + vLLM | 视频帧分析 |
| 嵌入模型 | bge-large-zh-v1.5 (1024维) | 向量化 |
| 重排器 | bge-reranker-v2-m3 | 检索重排 |
| 向量数据库 | Milvus 2.4.4 | 语义检索 |
| 关系数据库 | MySQL 8.4 | 业务数据 |
| 对象存储 | MinIO | 视频/截图线上存储 |
| 视频协议 | RTSP | 持续拉流 |
| 部署 | Docker Compose | 全离线私有化 |
| GPU | RTX PRO 6000 × 2 | 推理加速 |

## 数据建模

### ER 关系

```
museum_storage_room（库房）
  ├── museum_camera（摄像头）
  │     ├── museum_source_video（原始视频，3h/段）
  │     │     ├── museum_person_segment（人物视频段）
  │     │     │     └── museum_source_video_segment（动作片段，60s/段）
  │     │     └── museum_event（底层事件）
  │     │           ├── museum_rule_hit（规则命中快照）
  │     │           └── museum_event_aggregate（会话级聚合事件）
  │     └── ...
  └── museum_rule（规则定义）
```

### 核心表设计

**museum_storage_room** — 库房
```sql
CREATE TABLE museum_storage_room (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '库房名称',
    code VARCHAR(50) UNIQUE COMMENT '库房编号',
    location VARCHAR(200) COMMENT '位置',
    description TEXT COMMENT '描述',
    status TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**museum_camera** — 摄像头
```sql
CREATE TABLE museum_camera (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_id BIGINT NOT NULL COMMENT '所属库房',
    name VARCHAR(100) NOT NULL COMMENT '摄像头名称',
    rtsp_url VARCHAR(500) NOT NULL COMMENT 'RTSP拉流地址',
    segment_duration INT DEFAULT 10800 COMMENT '视频分段时长(秒)，默认3h',
    status TINYINT DEFAULT 1 COMMENT '1在线 2离线 3拉流中',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY REFERENCES museum_storage_room(id)
);
```

**museum_source_video** — 原始视频
```sql
CREATE TABLE museum_source_video (
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
```

**museum_person_segment** — 人物视频段
```sql
CREATE TABLE museum_person_segment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_video_id BIGINT NOT NULL,
    start_time FLOAT NOT NULL COMMENT '开始时间(秒)',
    end_time FLOAT NOT NULL COMMENT '结束时间(秒)',
    person_count INT COMMENT '检测到的人数(偏向值)',
    local_path VARCHAR(500) COMMENT '切片本地路径',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_video_id) REFERENCES museum_source_video(id)
);
```

**museum_source_video_segment** — 动作片段(60s切片)
```sql
CREATE TABLE museum_source_video_segment (
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
```

**museum_rule** — 规则定义
```sql
CREATE TABLE museum_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '规则名称',
    code VARCHAR(50) UNIQUE COMMENT '规则编码',
    description TEXT COMMENT '规则描述',
    rule_type VARCHAR(50) COMMENT '规则类型: person_count/dress/behavior/posture',
    rule_config JSON COMMENT '规则配置参数',
    enabled TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**museum_event** — 底层事件
```sql
CREATE TABLE museum_event (
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**museum_rule_hit** — 规则命中快照
```sql
CREATE TABLE museum_rule_hit (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_id BIGINT NOT NULL,
    rule_id BIGINT NOT NULL,
    hit_time DATETIME NOT NULL,
    confidence FLOAT COMMENT '置信度',
    evidence_snapshCHAR(500) COMMENT '证据截图',
    detail TEXT COMMENT '命中详情',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES museum_event(id),
    FOREIGN KEY (rule_id) REFERENCES museum_rule(id)
);
```

**museum_event_aggregate** — 库房会话级聚合事件
```sql
CREATE TABLE museum_event_aggregate (
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
    FOREIGN KEY (room_id) REFERENCES museum_storage_room(id)
);
```

**museum_collection** — 藏品
```sql
CREATE TABLE museum_collection (
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
```

## 视频分析管线设计

```
原始视频(3h)
  │
  ├─ Step1: YOLO11 跳帧粗扫 (class=0, 跳帧间隔可配)
  │    └─ 输出: 粗略人物时间区间列表
  │
  ├─ Step2: 扩帧精扫 (前后±5秒)
  │    └─ 输出: 精确人物时间区间
  │
  ├─ Step3: 短窗口合并 (gap<3秒则合并)
  │    └─ 输出: 人物大片段 (museum_person_segment)
  │
  ├─ Step4: 60s切分 + 1秒1帧抽图
  │    └─ 输出: 动作片段 + 关键帧截图
  │
  ├─ Step5: Qwen3.5 多模态逐片段分析
  │    └─ 输入: 60张截图 + YOLO/Pose/Tracker结果
  │    └─ 输出: 片段分析结论
  │
  ├─ Step6: 增量合并结论 (上下文压缩)
  │    └─ 每分析一个片段，与前序结论合并
  │
  ├─ Step7: 裁判模型 + 规则匹配
  │    └─ 输入: 合并结论 + 规则列表
  │    └─ 输出: 最终事件 + 规则命中
  │
  └─ Step8: 向量化ilvus
       └─ 库房+摄像头+时间+事件详情ing
```

## NLP 检索架构

```
用户自然语言提问
  → Qwen3-32B 意图解析 + 关键词提取
  → bge-large-zh-v1.5 向量化 query
  → Milvus 向量检索 Top-K
  → bge-reranker-v2-m3 重排序
  → Qwen3-32B 组织回答 + 引用证据
  → 返回结构化结果(时间/库房/摄像头/事件/视频链接)
```

## 项目目录结构

```
museum-video-monitor/
├── .kiro/
│   ├── specs/
│   └── steering/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 入口
│   │   ├── config.py          # 配置
│   │   ├── database.py        # 数据库连接
│   │   ├── models/            # SQLAlchemy 模型
│   │   │   ├── room.py
│   │   │   ├── camera.py
│   │   │   ├── vide │   │   ├── segment.py
│   │   │   ├── event.py
│   │   │   ├── rule.py
│   │   │   ├── collection.py
│   │   │   └── user.py
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── api/               # 路由
│   │   │   ├── rooms.py
│   │   │   ├── cameras.py
│   │   │   ├── videos.py
│   │   │   ├── events.py
│   │   │   ├── rules.py
│   │   │   ├── chat.py
│   │   │   ├── collections.py
│   │   │   └── auth.py
│   │   ├── services/          # 业务逻辑
│   │   │   ├── video_puller.py      # RTSP 拉流
│   │   │   ├── video_analyzer.py    # 分析调度
│   │   │   ├── yolo_detector.py     # YOLO 检测
│   │   │   ├── pose_tracker.py      # 姿态追踪
│   │   │   ├── llm_analyzer.py      # 大模型分析
│   │   │   ├── rule_engine.py       # 规则引擎
│   │   │   ├── milvus_service.py    # 向量存储
│   │   │   ├── rag_service.py       # RAG 检索
│   │   │   └── storage_service.py   # 文件存储
│   │   └── utils/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard/
│   │   │   ├── Room/
│   │   │   ├── Camera/
│   │   │   ├── Video/
│   │   │   ├── Event/
│   │   │   ├── Rule/
│   │   │   ├── Chat/
│   │   │   ├── Collection/
│   │   │   └── System/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── store/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── init.sql                    # 数据库初始化
└── README.md
```

## 部署架构

```yaml
# docker-compose.yml 服务清单
services:
  frontend:     React 前端 (nginx)
  backend:      FastAPI 后端
  mysql:        MySQL 8.4
  milvus:       Milvus 2.4.4 (+ etcd + minio)
  vllm-text:  2B 文本推理 (GPU0)
  vllm-vision:  Qwen3.5-35B-A3B 多模态 (GPU1)
  minio:        对象存储
```
