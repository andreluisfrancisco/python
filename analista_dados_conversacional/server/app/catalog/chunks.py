"""Catálogo semântico do schema analista.

Um chunk por tabela, mais um chunk fixo de métricas. O schema é pequeno:
quebrar uma definição de tabela no meio piora o SQL, então o corte é por
objeto, não por quantidade de tokens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaChunk:
    object_name: str
    text: str


CHUNKS: tuple[SchemaChunk, ...] = (
    SchemaChunk(
        "metricas",
        """
Métricas oficiais da rede de lojas Aurora. Use estas definições.

- Faturamento: soma de itens_pedido.quantidade * itens_pedido.preco_unitario * (1 - itens_pedido.desconto).
  Só entram pedidos com status = 'pago'. Cancelado e pendente ficam de fora.
- O preço cobrado está em itens_pedido.preco_unitario. produtos.preco é o preço de tabela atual e não mede venda.
- Ticket médio: faturamento dividido pela quantidade de pedidos pagos (COUNT DISTINCT de pedidos.id).
- Taxa de cancelamento: quantidade de pedidos cancelados dividida pela quantidade total de pedidos.
- desconto é uma fração de 0 a 1. 0.10 significa 10%.
- Moeda: real (BRL). Arredonde dinheiro com ROUND(..., 2).
- O fato de vendas é de 2025 (pedidos.criado_em). clientes.cliente_desde pode ser anterior.
- Canais: loja, site, app. Segmentos de cliente: varejo, pj, vip.
- Se a pergunta não disser o período, o status ou a loja, e o histórico também não tiver isso, peça esclarecimento.
- Numa resposta de um único número, a coluna deve se chamar valor. Não acrescente colunas que a pergunta não pediu.
- Qualifique as tabelas com o schema analista.
""".strip(),
    ),
    SchemaChunk(
        "regioes",
        """
Tabela analista.regioes. Região comercial da rede.
Colunas: id smallint PK, nome text. Valores: Sudeste, Sul, Nordeste, Centro-Oeste, Norte.
Relação: analista.lojas.regiao_id aponta para regioes.id.
""".strip(),
    ),
    SchemaChunk(
        "lojas",
        """
Tabela analista.lojas. Loja física que registrou o pedido, inclusive quando o canal é site ou app.
Colunas: id smallint PK, nome text, cidade text, uf char(2), regiao_id smallint FK para analista.regioes.
UFs das lojas: SP, PR, RS, BA, PE, GO, AM.
Para faturamento por UF da venda, use lojas.uf via pedidos.loja_id. A UF do cliente pode ser outra.
""".strip(),
    ),
    SchemaChunk(
        "vendedores",
        """
Tabela analista.vendedores. Pessoa que atendeu o pedido.
Colunas: id smallint PK, nome text, loja_id smallint FK para analista.lojas, admissao date.
No seed, o pedido usa a loja do próprio vendedor.
""".strip(),
    ),
    SchemaChunk(
        "categorias",
        """
Tabela analista.categorias. Categoria do produto.
Colunas: id smallint PK, nome text.
Valores: Eletrônicos, Casa, Esporte, Mercado, Beleza, Escritório.
Relação: analista.produtos.categoria_id.
""".strip(),
    ),
    SchemaChunk(
        "produtos",
        """
Tabela analista.produtos. Cadastro atual de produto.
Colunas: id smallint PK, nome text, categoria_id smallint FK, preco numeric (preço de tabela, não usar para faturamento).
Há 12 produtos. O id 12, Kit Corporativo Aurora, não tem itens vendidos.
""".strip(),
    ),
    SchemaChunk(
        "clientes",
        """
Tabela analista.clientes.
Colunas: id smallint PK, nome text, segmento text (varejo, pj, vip), cidade text, uf char(2), cliente_desde date.
A UF do cliente é o endereço do cliente, não a UF da loja.
Cliente novo em 2025: cliente_desde dentro de 2025.
""".strip(),
    ),
    SchemaChunk(
        "pedidos",
        """
Tabela analista.pedidos. Cabeçalho do pedido. 120 pedidos, todos com criado_em em 2025.
Colunas: id integer PK, cliente_id FK, loja_id FK, vendedor_id FK, criado_em date, status text, canal text.
status: pago, pendente, cancelado. canal: loja, site, app.
Faturamento não está nesta tabela. Some os itens em analista.itens_pedido.
""".strip(),
    ),
    SchemaChunk(
        "itens_pedido",
        """
Tabela analista.itens_pedido. Linha do pedido. Dois itens por pedido neste dataset.
Colunas: id integer PK, pedido_id FK para analista.pedidos, produto_id FK para analista.produtos,
quantidade integer, preco_unitario numeric, desconto numeric (fração).
Valor da linha: quantidade * preco_unitario * (1 - desconto).
""".strip(),
    ),
)

PINNED_CHUNKS = frozenset({"metricas"})
