from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import bad_request, service_unavailable
from app.schemas.chat import ChatResponse
from app.schemas.history import Turn
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.prompt_builder import PromptBuilder
from app.stores.conversation_store import ConversationStore
from app.stores.faiss_store import FaissStore
from app.stores.vector_map_store import VectorMapStore


class MemoryManager:
    def __init__(
        self,
        conversation_store: ConversationStore,
        vector_map_store: VectorMapStore,
        faiss_store: FaissStore,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        recent_turns: int,
        retrieve_top_k: int,
    ) -> None:
        self.conversation_store = conversation_store
        self.vector_map_store = vector_map_store
        self.faiss_store = faiss_store
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.prompt_builder = prompt_builder
        self.recent_turns = recent_turns
        self.retrieve_top_k = retrieve_top_k

    def chat(self, user_query: str) -> ChatResponse:
        user_query = user_query.strip()
        if not user_query:
            raise bad_request("message cannot be empty.")

        recent_turns = self.conversation_store.get_recent_turns(self.recent_turns)
        retrieved_turns = self._retrieve_turns(user_query)
        retrieved_turns = self._remove_recent_duplicates(recent_turns, retrieved_turns)

        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_user_prompt(
            recent_turns=recent_turns,
            retrieved_turns=retrieved_turns,
            user_query=user_query,
        )
        answer = self._generate_answer(system_prompt, user_prompt)
        turn = self.conversation_store.append_turn(user=user_query, assistant=answer)
        self._save_turn_vector(turn)

        return ChatResponse(
            answer=answer,
            turn_id=turn.turn_id,
            retrieved_turn_ids=[turn.turn_id for turn in retrieved_turns],
        )

    def _retrieve_turns(self, user_query: str) -> list[Turn]:
        try:
            query_vector = self.embedding_service.embed(user_query)
            faiss_ids = self.faiss_store.search(query_vector, self.retrieve_top_k)
            turn_ids = self.vector_map_store.resolve_turn_ids(faiss_ids)
            return self.conversation_store.get_turns_by_ids(turn_ids)
        except Exception as exc:
            raise service_unavailable(f"Failed to retrieve memory: {exc}") from exc

    def _generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        try:
            answer = self.llm_service.generate(system_prompt, user_prompt)
        except Exception as exc:
            raise service_unavailable(f"Failed to generate answer: {exc}") from exc

        if not answer:
            raise service_unavailable("LLM returned an empty answer.")
        return answer

    def _save_turn_vector(self, turn: Turn) -> None:
        try:
            turn_text = self.prompt_builder.build_turn_embedding_text(turn)
            turn_vector = self.embedding_service.embed(turn_text)
            faiss_id = self.faiss_store.add(turn_vector)
            self.vector_map_store.append(faiss_id=faiss_id, turn_id=turn.turn_id)
        except Exception as exc:
            raise service_unavailable(f"Failed to save turn vector: {exc}") from exc

    @staticmethod
    def _remove_recent_duplicates(recent_turns: list[Turn], retrieved_turns: list[Turn]) -> list[Turn]:
        recent_turn_ids = {turn.turn_id for turn in recent_turns}
        return [turn for turn in retrieved_turns if turn.turn_id not in recent_turn_ids]

    def list_history(self) -> list[Turn]:
        return self.conversation_store.list_turns()

    def list_recent_history(self, limit: int) -> list[Turn]:
        return self.conversation_store.get_recent_turns(limit)

    def clear_history(self) -> None:
        self.conversation_store.clear()
        self.vector_map_store.clear()
        self.faiss_store.clear()


@lru_cache
def get_memory_manager() -> MemoryManager:
    settings = get_settings()
    embedding_service = EmbeddingService(settings)
    return MemoryManager(
        conversation_store=ConversationStore(settings.conversation_path),
        vector_map_store=VectorMapStore(settings.vector_map_path),
        faiss_store=FaissStore(
            path=settings.faiss_index_path,
            dimension=embedding_service.dimension,
        ),
        embedding_service=embedding_service,
        llm_service=LLMService(settings),
        prompt_builder=PromptBuilder(),
        recent_turns=settings.recent_turns,
        retrieve_top_k=settings.retrieve_top_k,
    )
