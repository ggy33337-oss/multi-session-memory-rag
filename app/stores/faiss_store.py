from pathlib import Path

import faiss
import numpy as np


class FaissStore:
    def __init__(self, path: Path, dimension: int) -> None:
        self.path = path
        self.dimension = dimension
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.index = self._load_or_create_index()

    @property
    def total(self) -> int:
        return int(self.index.ntotal)

    def search(self, vector: list[float], top_k: int) -> list[int]:
        if top_k <= 0 or self.index.ntotal == 0:
            return []

        query = self._to_numpy([vector])
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))
        return [int(index) for index in indices[0] if int(index) >= 0]

    def add(self, vector: list[float]) -> int:
        faiss_id = int(self.index.ntotal)
        self.index.add(self._to_numpy([vector]))
        self.save()
        return faiss_id

    def clear(self) -> None:
        self.index = faiss.IndexFlatIP(self.dimension)
        if self.path.exists():
            self.path.unlink()

    def save(self) -> None:
        faiss.write_index(self.index, str(self.path))

    def _load_or_create_index(self) -> faiss.Index:
        if self.path.exists():
            index = faiss.read_index(str(self.path))
            if index.d != self.dimension:
                raise ValueError(
                    f"FAISS index dimension {index.d} does not match configured dimension {self.dimension}."
                )
            return index
        return faiss.IndexFlatIP(self.dimension)

    def _to_numpy(self, vectors: list[list[float]]) -> np.ndarray:
        array = np.array(vectors, dtype="float32")
        if array.ndim != 2 or array.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension must be {self.dimension}.")
        faiss.normalize_L2(array)
        return array

