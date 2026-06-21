# 多会话长期记忆 RAG 问答系统

本项目是一个适合实习展示的多会话长期记忆 RAG 问答系统，支持会话级历史检索和全局文档知识库问答。

代码复杂度控制在简单函数调用级别，不做多余缓存、不做复杂依赖注入、不引入任务队列。

## 核心流程

```text
User
  ↓
FastAPI route
  ↓
service 函数编排业务
  ↓
repository 函数读写 PostgreSQL / pgvector
  ↓
Prompt + LLM
  ↓
保存本轮对话和向量
```

## 技术栈

| 模块 | 选择 | 说明 |
|---|---|---|
| 后端 | FastAPI | 提供 sessions/chat/history/documents/health 接口 |
| 数据库 | PostgreSQL | 保存会话、对话、文档、文档切片 |
| 向量检索 | pgvector | 数据库内完成相似度检索 |
| LLM | DashScope OpenAI-compatible | `generate_answer()` |
| Embedding | DashScope OpenAI-compatible | `embed_text()` |
| 文件上传 | 本地 uploads 目录 | 只保存上传原文件 |
| 文档解析 | pypdf + 文本读取 | 支持 `.txt`、`.md`、`.pdf` |
| 接口文档 | FastAPI `/docs` | 自动生成 Swagger |

## 当前目录结构

```text
app/
  api/                 # 路由层：接收请求，调用 service 函数
  core/                # 配置、错误处理、数据库建表
  repositories/        # 数据层：SQL 和 pgvector 查询
  schemas/             # 请求/响应结构
  services/            # 业务层：聊天、文档、embedding、llm、prompt
web/                   # 静态前端页面
data/documents/uploads # 上传原文件保存目录
```

## 调用逻辑

### 对话

```text
routes_chat.chat()
  -> memory_manager.chat()
    -> embed_text(user_query)
    -> conversation_repository.get_recent_turns(session_id)
    -> conversation_repository.search_similar_turns(session_id)
    -> document_service.search_by_vector()
    -> prompt_builder.build_user_prompt()
    -> generate_answer()
    -> embed_text(user + assistant)
    -> conversation_repository.append_turn(session_id)
```

说明：

- 会话历史按 `session_id` 隔离。
- 最近会话、历史相似检索只检索当前会话窗口。
- 文档检索不绑定 `session_id`，所有会话窗口共享同一个文档知识库。

### 文档上传

```text
routes_documents.upload_document()
  -> document_service.upload_document()
    -> save_upload_file()
    -> extract_text()
    -> split_text()
    -> embed_text(chunk)
    -> document_repository.append_document_with_chunks()
```

## 启动

安装依赖：

```bash
pip install -r requirements.txt
```

启动 PostgreSQL + pgvector：

```bash
docker compose up -d
```

配置 `.env`：

```env
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_URL=postgresql://memory_user:memory_password@127.0.0.1:5432/memory_rag

OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

启动后端：

```bash
python -m app.main
```

访问：

- 前端页面: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`

说明：项目默认端口是 `8000`。如果你在本地 `.env` 中把 `APP_PORT` 改成了其他端口，例如 `8001`，则访问地址也要同步改为 `http://127.0.0.1:8001/` 和 `http://127.0.0.1:8001/docs`。

## 接口

```http
GET /sessions
POST /sessions
DELETE /sessions/{session_id}

POST /chat
GET /history?session_id=1
GET /history/recent?session_id=1&limit=5
DELETE /history?session_id=1

POST /documents
GET /documents
GET /documents/search?query=项目如何部署
DELETE /documents/{document_id}
DELETE /documents
```

## 数据存储

旧的本地业务数据文件存储已经移除。

现在只使用 PostgreSQL + pgvector：

| 表 | 作用 |
|---|---|
| `conversation_sessions` | 保存会话窗口标题、创建时间、更新时间 |
| `conversation_turns` | 保存每轮用户问题、助手回答、所属会话和对话向量 |
| `documents` | 保存上传文档基本信息 |
| `document_chunks` | 保存文档切片内容和切片向量 |

本地 `data/documents/uploads` 只保存上传的原始文件，不再保存向量索引或 JSON 业务数据。

## 简历描述

基于 FastAPI、PostgreSQL pgvector 和大模型 API 实现多会话长期记忆 RAG 问答系统，支持多会话隔离、文档上传解析、向量化切片、语义检索、多轮对话记忆和 Prompt 上下文增强。
