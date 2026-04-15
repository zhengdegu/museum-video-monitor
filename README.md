# 博物馆视频智能监控分析平台

基于 AI 的博物馆视频监控系统，复用现有摄像头，纯软件方案实现实时视频分析、异常事件检测、智能报警推送、RAG 智能问答和藏品管理。通过 YOLO 目标检测、多模态大模型分析和向量化检索，实现对博物馆场景的自动化智能监控。

## 核心能力

- **RTSP 实时拉流** — 自动接入现有摄像头，ffmpeg 按时间窗口切片，无需更换硬件
- **AI 视频分析管线** — YOLO 粗扫→精扫→合并→切片→多模态 LLM 分析→裁判判定→向量化存储
- **实时报警推送** — 异常事件秒级推送到飞书/钉钉，risk_level ≥ 2 自动触发
- **RAG 智能问答** — 基于 Milvus 向量检索 + 大模型，自然语言查询历史事件
- **规则引擎** — 结构化 JSON 匹配，支持人数、着装、行为、姿态等多维度规则
- **藏品盘点** — 库房管理、摄像头管理、藏品台账
- **任务队列** — 分析任务持久化追踪，启动时自动恢复未完成任务，最多重试 3 次
- **磁盘自动清理** — 已分析视频保留 24 小时后自动清理

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI / SQLAlchemy / MySQL 8.4 / Milvus / MinIO |
| AI | YOLO11 / OpenCV / 姿态追踪 / vLLM / RAG |
| 前端 | React 18 / TypeScript / Ant Design 5 / Vite |
| 大模型 | 支持本地 vLLM / 通义千问 / DeepSeek / OpenAI（兼容 OpenAI 协议） |
| 部署 | Docker Compose / All-in-One 镜像 / Nginx / GitHub Actions CI/CD |

## 项目结构

```
├── backend/                    # 后端服务 (FastAPI)
│   └── app/
│       ├── api/                # 接口路由 (认证/摄像头/视频/事件/规则/聊天/盘点)
│       ├── models/             # 数据库模型 (含 analysis_task 任务表)
│       ├── schemas/            # Pydantic 数据模型
│       ├── services/           # 业务逻辑
│       │   ├── video_analyzer.py   # 视频分析管线调度
│       │   ├── video_puller.py     # RTSP 拉流 + ffmpeg 切片
│       │   ├── yolo_detector.py    # YOLO 目标检测
│       │   ├── llm_analyzer.py     # 多模态大模型分析 + 裁判判定
│       │   ├── rag_service.py      # RAG 检索 + 流式问答
│       │   ├── rule_engine.py      # 结构化规则引擎
│       │   ├── alert_service.py    # 飞书/钉钉报警推送
│       │   ├── task_service.py     # 分析任务队列
│       │   ├── cleanup_service.py  # 磁盘自动清理
│       │   ├── milvus_service.py   # Milvus 向量存储
│       │   └── storage_service.py  # MinIO 对象存储
│       └── utils/              # 工具函数 (鉴权/RBAC/安全)
│   └── tests/                  # 测试用例 (pytest)
├── frontend/                   # 前端应用 (React + Vite)
│   └── src/
│       ├── pages/              # 页面 (Dashboard/Login/Chat/Room/Camera/Video/Event...)
│       ├── components/         # 公共组件 (ErrorBoundary/VideoPlayer)
│       ├── layouts/            # 布局 (WanderMap Design System)
│       └── utils/              # 请求封装
├── deploy/                     # 部署配置
│   ├── entrypoint.sh           # All-in-One 启动脚本
│   ├── supervisord.conf        # 多进程管理
│   └── nginx-allinone.conf     # Nginx 反代配置
├── docker-compose.yml          # 多容器编排
├── Dockerfile.allinone         # All-in-One 单镜像 (含 MySQL/Milvus/MinIO)
├── init.sql                    # 数据库初始化 (建表/索引/预置数据)
└── .env.example                # 环境变量模板
```

## 快速启动

### 方式一：Docker Compose（推荐开发环境）

```bash
cp .env.example .env
# 编辑 .env 填入必填项（SECRET_KEY、MYSQL_PASSWORD 等）

docker-compose up -d
```

### 方式二：All-in-One 单镜像（推荐生产部署）

```bash
docker build -f Dockerfile.allinone -t museum-monitor:latest .

docker run -d --name museum \
  --gpus all \
  -p 80:80 -p 8080:8080 -p 3306:3306 -p 9001:9001 -p 19530:19530 \
  -v museum-mysql:/var/lib/mysql \
  -v museum-minio:/data/minio \
  -v museum-milvus:/var/lib/milvus \
  -v museum-data:/app/data \
  -e SECRET_KEY=your-secret-key \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=your-password \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=your-minio-secret \
  museum-monitor:latest
```

### 启动后访问

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost |
| 后端 API | http://localhost:8080 |
| API 文档 | http://localhost:8080/docs |
| MinIO 控制台 | http://localhost:9001 |

## 大模型配置

支持多种大模型后端，只需修改 `.env`：

```env
# 本地 vLLM（需要 GPU）
VLLM_TEXT_URL=http://localhost:8000/v1
VLLM_TEXT_MODEL=Qwen3-32B
VLLM_VISION_MODEL=Qwen3.5-35B-A3B
VLLM_API_KEY=not-needed

# 通义千问（云端 API）
VLLM_TEXT_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VLLM_TEXT_MODEL=qwen-max
VLLM_VISION_MODEL=qwen-vl-max
VLLM_API_KEY=sk-your-key

# DeepSeek
VLLM_TEXT_URL=https://api.deepseek.com/v1
VLLM_TEXT_MODEL=deepseek-chat
VLLM_API_KEY=sk-your-key

# OpenAI
VLLM_TEXT_URL=https://api.openai.com/v1
VLLM_TEXT_MODEL=gpt-4o
VLLM_VISION_MODEL=gpt-4o
VLLM_API_KEY=sk-your-key
```

## 报警推送

支持飞书和钉钉 webhook 推送，在 `.env` 中配置：

```env
ALERT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
ALERT_WEBHOOK_TYPE=feishu  # feishu / dingtalk
```

当检测到中高风险事件（risk_level ≥ 2）时自动推送报警，包含事件类型、库房、摄像头、风险等级、AI 结论摘要。

## 默认账号

| 用户名 | 密码 |
|--------|------|
| admin  | admin123 |

## 安全特性

- SECRET_KEY 等敏感配置必须通过环境变量设置，无硬编码默认值
- RBAC 权限中间件，基于角色的接口级权限控制
- 登录接口 Rate Limiting（5 次/分钟/IP）
- 文件上传路径遍历校验
- CORS 来源可配置

## CI/CD

GitHub Actions 自动构建三个 Docker 镜像：

- `ghcr.io/{owner}/museum-video-monitor-backend`
- `ghcr.io/{owner}/museum-video-monitor-frontend`
- `ghcr.io/{owner}/museum-video-monitor-allinone`

推送到 master 自动构建，打 `v*` 标签自动发版。CI 包含后端测试门禁。

## License

MIT
