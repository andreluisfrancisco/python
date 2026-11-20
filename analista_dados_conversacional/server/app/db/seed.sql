-- Dataset fictício da rede Aurora. Pedidos cobrem 2025.
-- O produto 12 não entra em itens_pedido de propósito (pergunta "nunca vendido").

INSERT INTO analista.regioes (id, nome) VALUES
  (1, 'Sudeste'),
  (2, 'Sul'),
  (3, 'Nordeste'),
  (4, 'Centro-Oeste'),
  (5, 'Norte')
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.lojas (id, nome, cidade, uf, regiao_id) VALUES
  (1, 'Aurora Paulista', 'São Paulo', 'SP', 1),
  (2, 'Aurora Campinas', 'Campinas', 'SP', 1),
  (3, 'Aurora Curitiba', 'Curitiba', 'PR', 2),
  (4, 'Aurora Porto Alegre', 'Porto Alegre', 'RS', 2),
  (5, 'Aurora Salvador', 'Salvador', 'BA', 3),
  (6, 'Aurora Recife', 'Recife', 'PE', 3),
  (7, 'Aurora Goiânia', 'Goiânia', 'GO', 4),
  (8, 'Aurora Manaus', 'Manaus', 'AM', 5)
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.vendedores (id, nome, loja_id, admissao) VALUES
  (1, 'Marina Alves', 1, DATE '2022-03-01'),
  (2, 'Bruno Pires', 2, DATE '2021-07-15'),
  (3, 'Camila Rocha', 3, DATE '2023-01-10'),
  (4, 'Diego Martins', 4, DATE '2020-11-02'),
  (5, 'Helena Souza', 5, DATE '2022-08-20'),
  (6, 'Igor Nunes', 6, DATE '2024-02-01'),
  (7, 'Julia Ferreira', 7, DATE '2023-05-12'),
  (8, 'Kaio Mendes', 8, DATE '2021-09-30'),
  (9, 'Larissa Teixeira', 1, DATE '2024-04-18'),
  (10, 'Mateus Carvalho', 2, DATE '2019-12-01'),
  (11, 'Nina Barbosa', 3, DATE '2022-06-06'),
  (12, 'Otávio Lima', 4, DATE '2023-10-09')
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.categorias (id, nome) VALUES
  (1, 'Eletrônicos'),
  (2, 'Casa'),
  (3, 'Esporte'),
  (4, 'Mercado'),
  (5, 'Beleza'),
  (6, 'Escritório')
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.produtos (id, nome, categoria_id, preco) VALUES
  (1, 'Fone Aurora Wave', 1, 199.90),
  (2, 'Teclado Compacto', 1, 249.00),
  (3, 'Cafeteira Pressão', 2, 329.50),
  (4, 'Jogo de Panelas', 2, 459.00),
  (5, 'Tênis Corrida', 3, 379.90),
  (6, 'Garrafa Térmica', 3, 89.00),
  (7, 'Café Especial 500g', 4, 42.50),
  (8, 'Azeite 500ml', 4, 38.90),
  (9, 'Kit Skincare', 5, 129.00),
  (10, 'Perfume Citrus', 5, 219.00),
  (11, 'Cadeira de Escritório', 6, 890.00),
  (12, 'Kit Corporativo Aurora', 6, 1500.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.clientes (id, nome, segmento, cidade, uf, cliente_desde) VALUES
  (1, 'Ana Ribeiro', 'vip', 'São Paulo', 'SP', DATE '2023-02-11'),
  (2, 'Oficina Leste LTDA', 'pj', 'Guarulhos', 'SP', DATE '2022-06-01'),
  (3, 'Carlos Mendes', 'varejo', 'Campinas', 'SP', DATE '2024-01-20'),
  (4, 'Beatriz Kunz', 'vip', 'Curitiba', 'PR', DATE '2023-09-14'),
  (5, 'Mercado Sul ME', 'pj', 'Porto Alegre', 'RS', DATE '2021-04-03'),
  (6, 'Diego Farias', 'varejo', 'Salvador', 'BA', DATE '2024-11-02'),
  (7, 'Fernanda Luz', 'vip', 'Recife', 'PE', DATE '2022-12-19'),
  (8, 'Clínica Horizonte', 'pj', 'Goiânia', 'GO', DATE '2023-07-07'),
  (9, 'Gabriel Pinto', 'varejo', 'Manaus', 'AM', DATE '2025-01-15'),
  (10, 'Helena Dias', 'vip', 'São Paulo', 'SP', DATE '2025-02-02'),
  (11, 'Studio Norte', 'pj', 'Belém', 'PA', DATE '2025-03-18'),
  (12, 'Igor Salles', 'varejo', 'Campinas', 'SP', DATE '2025-03-28'),
  (13, 'Joana Klein', 'vip', 'Florianópolis', 'SC', DATE '2025-04-09'),
  (14, 'Padaria Central', 'pj', 'Salvador', 'BA', DATE '2025-05-01'),
  (15, 'Lucas Amaral', 'varejo', 'Recife', 'PE', DATE '2025-05-22'),
  (16, 'Marina Costa', 'vip', 'Brasília', 'DF', DATE '2025-06-11'),
  (17, 'Escola Horizonte', 'pj', 'Goiânia', 'GO', DATE '2025-07-01'),
  (18, 'Paulo Neri', 'varejo', 'Manaus', 'AM', DATE '2025-08-19'),
  (19, 'Renata Vidal', 'vip', 'Curitiba', 'PR', DATE '2025-09-30'),
  (20, 'Sofia Martins', 'varejo', 'Porto Alegre', 'RS', DATE '2025-11-12')
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.pedidos (id, cliente_id, loja_id, vendedor_id, criado_em, status, canal)
SELECT
  g + 1,
  1 + (g % 20),
  ((g % 12) % 8) + 1,
  1 + (g % 12),
  DATE '2025-01-01' + (g * 3),
  CASE
    WHEN g % 17 = 0 THEN 'cancelado'
    WHEN g % 11 = 0 THEN 'pendente'
    ELSE 'pago'
  END,
  CASE g % 3
    WHEN 0 THEN 'loja'
    WHEN 1 THEN 'site'
    ELSE 'app'
  END
FROM generate_series(0, 119) AS g
ON CONFLICT (id) DO NOTHING;

INSERT INTO analista.itens_pedido (
  id, pedido_id, produto_id, quantidade, preco_unitario, desconto
)
SELECT
  g + 1,
  (g / 2) + 1,
  1 + (g % 11),
  1 + (g % 4),
  (SELECT preco FROM analista.produtos WHERE id = 1 + (g % 11)),
  CASE g % 5 WHEN 0 THEN 0.100 WHEN 1 THEN 0.050 ELSE 0.000 END
FROM generate_series(0, 239) AS g
ON CONFLICT (id) DO NOTHING;
