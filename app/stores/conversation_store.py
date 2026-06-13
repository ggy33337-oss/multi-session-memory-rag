import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.schemas.history import Turn


class ConversationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_raw([])

    def list_turns(self) -> list[Turn]:
        raw_turns = self._read_raw()
        return [Turn.model_validate(turn) for turn in raw_turns]

    def get_recent_turns(self, limit: int) -> list[Turn]:
        if limit <= 0:
            return []
        return self.list_turns()[-limit:]

    def get_turns_by_ids(self, turn_ids: list[int]) -> list[Turn]:
        if not turn_ids:
            return []
        turn_id_set = set(turn_ids)
        turns = [turn for turn in self.list_turns() if turn.turn_id in turn_id_set]
        order = {turn_id: index for index, turn_id in enumerate(turn_ids)}
        return sorted(turns, key=lambda turn: order.get(turn.turn_id, len(order)))

    def append_turn(self, user: str, assistant: str) -> Turn:
        raw_turns = self._read_raw()
        next_turn_id = self._next_turn_id(raw_turns)
        turn = Turn(
            turn_id=next_turn_id,
            user=user,
            assistant=assistant,
            created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        )
        raw_turns.append(turn.model_dump())
        self._write_raw(raw_turns)
        return turn

    def clear(self) -> None:
        self._write_raw([])

    def _read_raw(self) -> list[dict]:
        if not self.path.exists():
            return []
        content = self.path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError(f"{self.path} must contain a JSON array.")
        return data

    def _write_raw(self, data: list[dict]) -> None:
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

    @staticmethod
    def _next_turn_id(raw_turns: list[dict]) -> int:
        if not raw_turns:
            return 1
        return max(int(turn.get("turn_id", 0)) for turn in raw_turns) + 1
