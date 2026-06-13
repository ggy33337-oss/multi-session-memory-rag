from app.schemas.history import Turn


class PromptBuilder:
    @staticmethod
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
        self,
        recent_turns: list[Turn],
        retrieved_turns: list[Turn],
        user_query: str,
    ) -> str:
        return "\n\n".join(
            [
                "以下是最近对话：\n" + self._format_turns(recent_turns),
                "以下是从长期记忆中检索到的相关历史：\n" + self._format_turns(retrieved_turns),
                "当前用户问题：\n" + user_query,
                "回答要求：\n"
                "1. 优先结合最近对话\n"
                "2. 如果检索历史相关，可以自然引用\n"
                "3. 如果历史无关，不要强行使用\n"
                "4. 回答要清晰、具体、可执行",
            ]
        )

    @staticmethod
    def build_turn_embedding_text(turn: Turn) -> str:
        return f"User: {turn.user}\nAssistant: {turn.assistant}"

    @staticmethod
    def _format_turns(turns: list[Turn]) -> str:
        if not turns:
            return "无"

        blocks = []
        for turn in turns:
            blocks.append(
                f"[Turn {turn.turn_id}]\n"
                f"User: {turn.user}\n"
                f"Assistant: {turn.assistant}"
            )
        return "\n\n".join(blocks)
