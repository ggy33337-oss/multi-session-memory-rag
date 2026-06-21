from app.schemas.document import DocumentSearchResult
from app.schemas.history import Turn


def build_system_prompt() -> str:
    return "\n".join(
        [
            "你是一个有长期记忆能力的 AI 助手。",
            "你需要基于给定上下文回答用户问题。",
            "如果检索历史无关，不要强行使用。",
            "回答要清晰、具体、可执行，避免输出无意义前缀和多余标识符。",
        ]
    )


def build_user_prompt(
    recent_turns: list[Turn],
    retrieved_turns: list[Turn],
    retrieved_document_chunks: list[DocumentSearchResult],
    user_query: str,
) -> str:
    return "\n\n".join(
        [
            "以下是最近对话：\n" + format_turns(recent_turns),
            "以下是从长期记忆中检索到的相关历史：\n" + format_turns(retrieved_turns),
            "以下是从上传文档中检索到的相关片段：\n"
            + format_document_chunks(retrieved_document_chunks),
            "当前用户问题：\n" + user_query,
            "回答要求：\n"
            "1. 优先结合最近对话\n"
            "2. 如果检索历史相关，可以自然引用\n"
            "3. 如果历史无关，不要强行使用\n"
            "4. 如果文档片段相关，可以引用文档内容并说明来源文件\n"
            "5. 回答要清晰、具体、可执行",
        ]
    )


def build_turn_embedding_text(user: str, assistant: str) -> str:
    return f"User: {user}\nAssistant: {assistant}"


def format_turns(turns: list[Turn]) -> str:
    if not turns:
        return "无"

    blocks = []
    for turn in turns:
        blocks.append(
            f"[Turn {turn.turn_index}]\n"
            f"User: {turn.user}\n"
            f"Assistant: {turn.assistant}"
        )
    return "\n\n".join(blocks)


def format_document_chunks(chunks: list[DocumentSearchResult]) -> str:
    if not chunks:
        return "无"

    blocks = []
    for chunk in chunks:
        blocks.append(
            f"[Document {chunk.document_id} | Chunk {chunk.chunk_id} | {chunk.filename}]\n"
            f"{chunk.content}"
        )
    return "\n\n".join(blocks)
