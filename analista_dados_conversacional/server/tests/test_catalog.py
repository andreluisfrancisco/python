from app.catalog.chunks import CHUNKS
from app.catalog.retrieval import select_chunk_names


def test_metricas_entram_mesmo_fora_do_ranking():
    available = [chunk.object_name for chunk in CHUNKS]
    chosen = select_chunk_names(available, ["pedidos", "lojas", "clientes", "produtos"], top_k=2)
    assert chosen[0] == "metricas"
    assert chosen[1:] == ["pedidos", "lojas"]


def test_sem_ranking_entra_o_catalogo_inteiro():
    available = [chunk.object_name for chunk in CHUNKS]
    assert select_chunk_names(available, [], top_k=2) == available
