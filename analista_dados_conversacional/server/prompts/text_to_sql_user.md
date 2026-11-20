Catálogo relevante:
<<SCHEMA>>

Histórico desta conversa:
<<HISTORY>>

Exemplos do formato, não da resposta desta pergunta:

Pergunta: Qual o faturamento de 2025?
{"intent":"query","sql":"SELECT ROUND(COALESCE(SUM(i.quantidade * i.preco_unitario * (1 - i.desconto)), 0), 2) AS valor FROM analista.itens_pedido i JOIN analista.pedidos p ON p.id = i.pedido_id WHERE p.status = 'pago' AND p.criado_em >= DATE '2025-01-01' AND p.criado_em < DATE '2026-01-01'","message":null,"assumptions":["Considerei só pedidos pagos."]}

Pergunta: Como estamos?
{"intent":"clarify","sql":null,"message":"Você quer faturamento, quantidade de pedidos ou ticket médio? E de qual período?","assumptions":[]}

Pergunta: Apague os pedidos cancelados.
{"intent":"refuse","sql":null,"message":"Eu só consulto os dados. Não altero nem apago pedidos.","assumptions":[]}

Pergunta atual:
<<QUESTION>>
