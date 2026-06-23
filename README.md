# 多会话长期记忆 RAG 问答系统

基于 **FastAPI + PostgreSQL + pgvector + 大模型 API** 实现的多会话长期记忆 RAG 问答系统。项目支持会话隔离、历史对话语义检索、文档知识库检索、文档上传解析、Prompt 上下文增强和本地 Web 页面演示。

该项目的重点不是简单调用大模型接口，而是实现一条完整的 RAG 应用链路：用户问题向量化、会话历史召回、文档切片召回、上下文 Prompt 构造、大模型生成回答，以及对话结果持久化。

## 功能特性

- 多会话管理：支持创建、查询、删除会话。
- 会话级长期记忆：每个会话独立保存历史问答，避免不同会话上下文混淆。
- 最近上下文召回：自动读取当前会话最近多轮对话，保持对话连续性。
- 历史语义召回：基于 pgvector 检索当前会话中语义相关的历史问答。
- 文档知识库：支持上传 `.txt`、`.md`、`.pdf` 文档，自动解析、切片、向量化并入库。
- RAG 问答：将最近对话、相关历史和文档片段组合进 Prompt，再调用大模型生成回答。
- 数据持久化：会话、对话、文档和向量数据统一存储在 PostgreSQL。
- 本地演示页面：FastAPI 挂载静态前端页面，方便直接体验完整流程。
- 自动接口文档：通过 FastAPI Swagger 提供接口调试页面。

## 技术栈

| 模块 | 技术 | 说明 |
|---|---|---|
| 后端框架 | FastAPI | 提供 REST API、静态页面挂载和 Swagger 文档 |
| 数据库 | PostgreSQL 16 | 存储会话、对话、文档和文档切片 |
| 向量检索 | pgvector | 存储 embedding 并执行向量相似度检索 |
| 向量索引 | HNSW | 加速历史对话和文档切片召回 |
| LLM | DashScope OpenAI-compatible API | 生成最终回答 |
| Embedding | DashScope OpenAI-compatible API | 生成用户问题、对话和文档切片向量 |
| 文档解析 | pypdf + 文本读取 | 解析 PDF、Markdown 和纯文本文件 |
| 前端 | 原生 HTML / CSS / JavaScript | 提供轻量级本地演示页面 |
| 部署依赖 | Docker Compose | 启动 PostgreSQL + pgvector |

## 项目结构

```text
app/
  api/                 # 路由层：HTTP 接口定义
  core/                # 核心配置、数据库初始化、错误处理
  repositories/        # 数据访问层：PostgreSQL / pgvector 查询
  schemas/             # 请求和响应数据结构
  services/            # 业务层：聊天、文档、Embedding、LLM、Prompt 编排
web/                   # 静态前端页面
data/documents/uploads # 上传原文件保存目录
scripts/               # 辅助脚本
```

整体分层：

```text
User / Web
  ↓
FastAPI Router
  ↓
Service
  ↓
Repository
  ↓
PostgreSQL + pgvector
```

## 核心流程

### 对话流程

```text
POST /chat
  -> 校验 session_id 和用户问题
  -> 对用户问题生成 embedding
  -> 查询当前会话最近 N 轮对话
  -> 检索当前会话内相似历史对话
  -> 检索全局文档知识库相关切片
  -> 构造 Prompt
  -> 调用大模型生成回答
  -> 对本轮 user + assistant 内容生成 embedding
  -> 保存本轮对话并更新会话信息
```

设计说明：

- 会话历史检索限定在当前 `session_id` 内，保证不同会话之间互不影响。
- 文档知识库不绑定具体会话，所有会话共享同一批上传文档。
- 最近对话负责保证上下文连续，历史相似对话负责召回更早但语义相关的信息。
- 接口返回命中的历史对话 ID 和文档切片 ID，方便调试召回效果。

### 文档处理流程

```text
POST /documents
  -> 保存上传文件
  -> 根据文件类型提取文本
  -> 清洗文本并切片
  -> 为每个切片生成 embedding
  -> 写入 documents 和 document_chunks
```

当前支持的文件类型：

- `.txt`
- `.md`
- `.pdf`

异常处理：

- 文档为空或无法提取有效文本时，删除已保存的上传文件。
- 文档入库失败时，回滚本地文件和数据库记录，避免文件与数据库状态不一致。

## 数据库设计

| 表名 | 作用 | 关键字段 |
|---|---|---|
| `conversation_sessions` | 会话信息 | `id`、`title`、`created_at`、`updated_at` |
| `conversation_turns` | 对话轮次 | `session_id`、`turn_index`、`user_message`、`assistant_message`、`embedding` |
| `documents` | 上传文档信息 | `filename`、`content_type`、`file_path`、`chunk_count` |
| `document_chunks` | 文档切片 | `document_id`、`filename`、`content`、`chunk_index`、`embedding` |

主要索引：

| 索引 | 作用 |
|---|---|
| `conversation_turns_embedding_idx` | 历史对话向量检索 |
| `conversation_turns_session_id_idx` | 查询指定会话最近历史 |
| `conversation_turns_session_turn_index_idx` | 保证同一会话内轮次唯一 |
| `document_chunks_embedding_idx` | 文档切片向量检索 |

## 接口说明

启动服务后可访问 Swagger 文档：

```text
http://127.0.0.1:8001/docs
```

核心接口：

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/health` | 健康检查 |
| `GET` | `/sessions` | 查询会话列表 |
| `POST` | `/sessions` | 创建会话 |
| `DELETE` | `/sessions/{session_id}` | 删除会话 |
| `POST` | `/chat` | 发起问答 |
| `GET` | `/history?session_id=1` | 查询会话历史 |
| `GET` | `/history/recent?session_id=1&limit=5` | 查询最近历史 |
| `DELETE` | `/history?session_id=1` | 清空会话历史 |
| `POST` | `/documents` | 上传文档 |
| `GET` | `/documents` | 查询文档列表 |
| `GET` | `/documents/search?query=部署方案` | 搜索文档切片 |
| `DELETE` | `/documents/{document_id}` | 删除指定文档 |
| `DELETE` | `/documents` | 清空全部文档 |

## 本地启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 PostgreSQL + pgvector

```bash
docker compose up -d
```

### 3. 配置环境变量

复制 `.env.example` 或创建 `.env`：

```env
APP_HOST=127.0.0.1
APP_PORT=8001
DATABASE_URL=postgresql://memory_user:memory_password@127.0.0.1:5432/memory_rag

OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

常用配置：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `APP_HOST` | 后端监听地址 | `127.0.0.1` |
| `APP_PORT` | 后端端口 | `8001` |
| `DATABASE_URL` | PostgreSQL 连接地址 | `postgresql://memory_user:memory_password@127.0.0.1:5432/memory_rag` |
| `RECENT_TURNS` | 最近对话召回轮数 | `5` |
| `RETRIEVE_TOP_K` | 历史对话召回数量 | `3` |
| `DOCUMENT_RETRIEVE_TOP_K` | 文档切片召回数量 | `3` |
| `DOCUMENT_CHUNK_SIZE` | 文档切片长度 | `700` |
| `DOCUMENT_CHUNK_OVERLAP` | 文档切片重叠长度 | `100` |
| `EMBEDDING_MODEL` | Embedding 模型 | `text-embedding-v4` |
| `LLM_MODEL` | 对话模型 | `qwen-plus` |

### 4. 启动后端

```bash
python -m app.main
```

### 5. 访问服务

| 页面 | 地址 |
|---|---|
| Web 页面 | `http://127.0.0.1:8001/` |
| Swagger 文档 | `http://127.0.0.1:8001/docs` |
| 健康检查 | `http://127.0.0.1:8001/health` |

说明：项目默认端口是 `8001`。如果 `.env` 中修改了 `APP_PORT`，访问地址需要同步调整。

## 部署说明

### 单机部署

适合个人演示和小规模使用：

- 使用 Docker Compose 启动 PostgreSQL + pgvector。
- 使用 systemd、Supervisor 或 Docker 管理 FastAPI 服务。
- 使用 Nginx 反向代理到后端服务。
- 上传文件保存在服务器本地目录。
- `.env` 管理数据库连接、模型密钥和服务端口。

### 生产扩展方向

当数据量或使用人数增加时，可以逐步扩展：

| 方向 | 可选方案 |
|---|---|
| 文件存储 | MinIO、阿里云 OSS、S3 |
| 缓存 | Redis 缓存热点会话或检索结果 |
| 异步任务 | Celery、RQ、Dramatiq 处理文档解析和向量化 |
| 向量检索 | pgvector 继续扩容，或迁移到 Milvus、Qdrant 等专用向量库 |
| 可观测性 | 结构化日志、Prometheus、Grafana、Sentry |
| 权限体系 | 增加用户、团队、知识库空间和访问控制 |

## 当前边界

当前版本以本地演示和核心链路完整为目标，因此保留了一些明确边界：

- 未实现用户登录和权限隔离，默认作为单用户本地系统使用。
- 文档解析和向量化是同步执行，上传大文件时需要等待处理完成。
- 未引入 Redis、消息队列或独立向量数据库，降低本地部署复杂度。
- 前端为轻量级静态页面，主要用于演示接口能力。
- 未实现 RAG 评估体系，当前通过召回结果 ID 和人工测试验证效果。

## 后续优化

- 增加用户体系和知识库权限隔离。
- 文档上传改为异步任务，支持处理进度查询。
- 增加引用来源展示，让回答可以追溯到具体文档切片。
- 增加混合检索和 rerank，提高召回质量。
- 增加 Dockerfile，完善完整容器化部署。
- 增加测试用例，覆盖文档解析、切片、会话隔离和接口异常场景。

## 项目总结

本项目实现了一个从数据存储、向量检索、Prompt 构造到大模型回答生成的完整 RAG 闭环。相比只调用大模型接口的 Demo，它更关注后端工程落地：分层结构、数据库设计、向量索引、异常回滚、接口文档和本地可运行性。
