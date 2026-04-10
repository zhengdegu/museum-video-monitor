# 博物馆视频智能监控分析平台

基于 AI 的博物馆视频监控系统，支持实时视频分析、异常事件检测、智能问答和藏品管理。通过 YOLO 目标检测、姿态追踪和大语言模型，实现对博物馆场景的自动化智能监控。

## 技术栈

**后端：** FastAPI / SQLAlchemy / MySQL 8.4 / Milvus (向量数据库) / MinIO (对象存储) / OpenAI SDK (vLLM 推理)

**AI 能力：** YOLOv8 目标检测 / OpenCV 视频处理 / 姿态追踪 / RAG 智能问答

**前端：** React 18 / TypeScript / Ant Design 5 / Zustand / Vite / flv.js

**基础设施：** Docker Compose / Nginx / vLLM (GPU 推理服务)

## 项目结构

```
├── backend/                # 后端服务 (FastAPI)
│   └── app/
│       ├── api/            # 接口路由 (认证/摄像头/视频/事件/规则/聊天等)
│       ├── models/         # 数据库模型
│       ├── schemas/        # Pydantic 数据模型
│       ├── services/       # 业务逻辑 (视频分析/LLM/向量检索/规则引擎等)
│       └── utils/          # 工具函数 (鉴权/依赖注入)
├── frontend/               # 前端应用 (React + Vite)
│   └── src/
│       ├── components/     # 页面组件
│       └── layouts/        # 布局组件
├── docker-compose.yml      # 容器编排
└── init.sql                # 数据库初始化脚本
```

## 快速启动

```bash
docker-compose up -d
```

启动后访问：
- 前端界面：http://localhost
- 后端 API：http://localhost:8080
- API 文档：http://localhost:8080/docs
- MinIO 控制台：http://localhost:9001

如需启用 GPU 推理服务（Qwen 模型），取消 `docker-compose.yml` 中 vLLM 相关注释并确保已安装 NVIDIA Container Toolkit。

## 默认账号

| 用户名 | 密码 |
|--------|------|
| admin  | admin123 |

## API 文档

启动后端服务后访问 [/docs](http://localhost:8080/docs) 查看 Swagger 交互式文档。
