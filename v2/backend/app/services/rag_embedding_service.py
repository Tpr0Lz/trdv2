from __future__ import annotations

import hashlib
import math


EMBEDDING_DIMENSIONS = 32


def embed_text(text: str) -> list[float]:
    """中文注释：MVP 使用确定性 embedding，避免测试和本地导入依赖外部服务。"""
    vector = [0.0 for _ in range(EMBEDDING_DIMENSIONS)]
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[index] += sign
    return _normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in text.replace("\n", " ").split() if token.strip()]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
