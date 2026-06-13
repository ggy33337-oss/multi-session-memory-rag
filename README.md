# Memory RAG API

第一版本地对话记忆增强系统，目标是跑通：

```text
User
  ↓
FastAPI
  ↓
Memory Manager
  ↓
Recent Turns + FAISS Retrieved Turns
  ↓
Prompt Builder
  ↓
LLM
  ↓
Response
  ↓
Save Turn + Embedding + FAISS
```

## 技术栈

| 模块 | 第一版选择 | 说明 |
|---|---|---|
| 后端框架 | FastAPI | 提供 `/chat`、`/history`、`/health` |
| 向量检索 | FAISS | 本地保存向量索引 |
| 历史存储 | `conversation.json` | 保存完整 User/Assistant Turn |
| 向量映射 | `vector_map.json` | 记录 FAISS index 与 `turn_id` 的关系 |
| Embedding | DashScope OpenAI-compatible | 封装成 `EmbeddingService` |
| LLM | DashScope OpenAI-compatible | 封装成 `LLMService` |
| 配置 | `.env` | 模型名、API Key、路径、TopK |
| 接口文档 | FastAPI `/docs` | 自动生成 Swagger |

## 核心规则

- 检索时：只对当前用户问题做 Embedding。
- 入库时：对完整 `User + Assistant` Turn 做 Embedding。
- 落盘时：`conversation.json` 只保存原始字段，不保存冗余 `embedding_text`。
- FAISS 只保存向量，完整文本从 `conversation.json` 读取。

## 数据文件

`data/conversation.json`

```json
[
  {
    "turn_id": 1,
    "user": "你好",
    "assistant": "你好",
    "created_at": "2026-06-12T10:30:00+08:00"
  }
]
```

`data/vector_map.json`

```json
[
  {
    "faiss_id": 0,
    "turn_id": 1
  }
]
```

## 目录结构

```text
app/
  main.py
  api/
    routes_chat.py
    routes_history.py
    routes_health.py
  core/
    config.py
    errors.py
  schemas/
    chat.py
    history.py
  services/
    memory_manager.py
    embedding_service.py
    llm_service.py
    prompt_builder.py
  stores/
    conversation_store.py
    faiss_store.py
    vector_map_store.py
data/
  conversation.json
  faiss.index
  vector_map.json
```

## 启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问：

- 前端页面: `http://127.0.0.1:8001/`
- API: `http://127.0.0.1:8001`
- Swagger: `http://127.0.0.1:8001/docs`
- ReDoc: `http://127.0.0.1:8001/redoc`

如果使用 `.env` 里的 `APP_HOST` 和 `APP_PORT` 启动：

```bash
python -m app.main
```

## 接口

### 健康检查

```http
GET /health
```

### 对话

```http
POST /chat
Content-Type: application/json

{
  "message": "审核Agent怎么设计？"
}
```

响应：

```json
{
  "answer": "模型回复",
  "turn_id": 1,
  "retrieved_turn_ids": []
}
```

`retrieved_turn_ids` 是本次从 FAISS 召回并参与上下文拼接的历史 Turn 编号，主要用于开发调试。

### 历史

```http
GET /history
GET /history/recent?limit=5
DELETE /history
```

## 模型配置

当前项目使用 DashScope 的 OpenAI 兼容接口：

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024
LLM_PROVIDER=openai
LLM_MODEL=qwen-plus
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

切换不同 embedding 维度后，建议清空旧索引：

```http
DELETE /history
```
