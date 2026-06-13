import json
from pathlib import Path


class VectorMapStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_raw([])

    def list_items(self) -> list[dict[str, int]]:
        return self._read_raw()

    def append(self, faiss_id: int, turn_id: int) -> None:
        items = self._read_raw()
        items.append({"faiss_id": faiss_id, "turn_id": turn_id})
        self._write_raw(items)

    def resolve_turn_ids(self, faiss_ids: list[int]) -> list[int]:
        if not faiss_ids:
            return []
        mapping = {item["faiss_id"]: item["turn_id"] for item in self._read_raw()}
        return [mapping[faiss_id] for faiss_id in faiss_ids if faiss_id in mapping]

    def clear(self) -> None:
        self._write_raw([])

    def _read_raw(self) -> list[dict[str, int]]:
        if not self.path.exists():
            return []
        content = self.path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError(f"{self.path} must contain a JSON array.")
        return data

    def _write_raw(self, data: list[dict[str, int]]) -> None:
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

