# 项目规则

## 技术栈约束
- 后端：FastAPI + Python 3.11+，异步优先
- 前端：React 18 + TypeScript + Ant Design
- 数据库：MySQL 8.4 + Milvus 2.4.4
- 所有 AI 推理通过 vLLM 本地部署，禁止调用外部 API
- 部署方式：Docker Compose，全离线私有化

## 代码风格
- Python：遵循 PEP8，使用 type hints
- TypeScript：严格模式，禁止 any
- API 统一返回格式：`{ code: number, data: T, message: string }`
- 所有异步函数必须有异常处理

## 视频分析约束
- 视频分析全部在本地完成，分析完成后才异步推送线上存储
- YOLO 检测固定 class=0（人物），输入尺寸 640
- 人物数量取偏向值（80%置信度，取同画面最多人数）
- 奔跑检测必须连续帧判定，单帧不算
- 片段切分 60s 一段，1秒1帧抽图

## 安全约束
- 全系统不联网不上云
- JWT 认证 + RBAC 权限控制
- 敏感配置通过环境变量注入
- 视频数据不允许外传
