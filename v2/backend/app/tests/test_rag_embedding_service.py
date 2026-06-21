from app.services.rag_embedding_service import cosine_similarity, embed_text


def test_embedding_is_deterministic_and_fixed_size():
    first = embed_text("SPY rates inflation")
    second = embed_text("SPY rates inflation")

    assert len(first) == 32
    assert first == second


def test_cosine_similarity_prefers_same_text():
    query = embed_text("SPY rates inflation")
    same = embed_text("SPY rates inflation")
    different = embed_text("SPY holdings sector weights")

    assert cosine_similarity(query, same) > cosine_similarity(query, different)
