-- Tabelas do projeto no database app, schema analista.
-- Antes, como superusuário: app/db/bootstrap_admin.sql
-- (extensão vector no schema public e papel analista_leitura).
-- Rode este script com o papel migration. O embedding tem 768 dimensões.

CREATE SCHEMA IF NOT EXISTS analista;

REVOKE ALL ON SCHEMA analista FROM PUBLIC;
GRANT USAGE ON SCHEMA analista TO developer, analista_leitura;

CREATE TABLE IF NOT EXISTS analista.regioes (
  id smallint PRIMARY KEY,
  nome text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS analista.lojas (
  id smallint PRIMARY KEY,
  nome text NOT NULL,
  cidade text NOT NULL,
  uf char(2) NOT NULL,
  regiao_id smallint NOT NULL REFERENCES analista.regioes (id)
);

CREATE TABLE IF NOT EXISTS analista.vendedores (
  id smallint PRIMARY KEY,
  nome text NOT NULL,
  loja_id smallint NOT NULL REFERENCES analista.lojas (id),
  admissao date NOT NULL
);

CREATE TABLE IF NOT EXISTS analista.categorias (
  id smallint PRIMARY KEY,
  nome text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS analista.produtos (
  id smallint PRIMARY KEY,
  nome text NOT NULL,
  categoria_id smallint NOT NULL REFERENCES analista.categorias (id),
  preco numeric(10, 2) NOT NULL CHECK (preco > 0)
);

CREATE TABLE IF NOT EXISTS analista.clientes (
  id smallint PRIMARY KEY,
  nome text NOT NULL,
  segmento text NOT NULL CHECK (segmento IN ('varejo', 'pj', 'vip')),
  cidade text NOT NULL,
  uf char(2) NOT NULL,
  cliente_desde date NOT NULL
);

CREATE TABLE IF NOT EXISTS analista.pedidos (
  id integer PRIMARY KEY,
  cliente_id smallint NOT NULL REFERENCES analista.clientes (id),
  loja_id smallint NOT NULL REFERENCES analista.lojas (id),
  vendedor_id smallint NOT NULL REFERENCES analista.vendedores (id),
  criado_em date NOT NULL,
  status text NOT NULL CHECK (status IN ('pago', 'pendente', 'cancelado')),
  canal text NOT NULL CHECK (canal IN ('loja', 'site', 'app'))
);

CREATE TABLE IF NOT EXISTS analista.itens_pedido (
  id integer PRIMARY KEY,
  pedido_id integer NOT NULL REFERENCES analista.pedidos (id),
  produto_id smallint NOT NULL REFERENCES analista.produtos (id),
  quantidade integer NOT NULL CHECK (quantidade > 0),
  preco_unitario numeric(10, 2) NOT NULL CHECK (preco_unitario > 0),
  desconto numeric(4, 3) NOT NULL CHECK (desconto >= 0 AND desconto < 1)
);

CREATE INDEX IF NOT EXISTS pedidos_criado_idx ON analista.pedidos (criado_em);
CREATE INDEX IF NOT EXISTS pedidos_status_idx ON analista.pedidos (status);
CREATE INDEX IF NOT EXISTS itens_pedido_pedido_idx ON analista.itens_pedido (pedido_id);
CREATE INDEX IF NOT EXISTS itens_pedido_produto_idx ON analista.itens_pedido (produto_id);

CREATE TABLE IF NOT EXISTS analista.usuarios (
  id uuid PRIMARY KEY,
  email text NOT NULL UNIQUE,
  senha_hash text NOT NULL,
  nome text NOT NULL,
  criado_em timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analista.conversas (
  id uuid PRIMARY KEY,
  usuario_id uuid NOT NULL REFERENCES analista.usuarios (id),
  titulo text NOT NULL,
  criada_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversas_usuario_idx ON analista.conversas (usuario_id, criada_em DESC);

CREATE TABLE IF NOT EXISTS analista.mensagens (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  conversa_id uuid NOT NULL REFERENCES analista.conversas (id) ON DELETE CASCADE,
  papel text NOT NULL CHECK (papel IN ('user', 'assistant')),
  conteudo text NOT NULL,
  sql text,
  criada_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mensagens_conversa_idx ON analista.mensagens (conversa_id, id);

CREATE TABLE IF NOT EXISTS analista.schema_chunks (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  object_name text NOT NULL UNIQUE,
  chunk_text text NOT NULL,
  embedding vector(768)
);

CREATE INDEX IF NOT EXISTS schema_chunks_embedding_idx
  ON analista.schema_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS analista.auditoria_sql (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  usuario_id uuid REFERENCES analista.usuarios (id),
  conversa_id uuid,
  pergunta text NOT NULL,
  sql text,
  status text NOT NULL,
  detalhe text,
  criada_em timestamptz NOT NULL DEFAULT now()
);

GRANT SELECT ON
  analista.regioes,
  analista.lojas,
  analista.vendedores,
  analista.categorias,
  analista.produtos,
  analista.clientes,
  analista.pedidos,
  analista.itens_pedido
TO analista_leitura;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  analista.usuarios,
  analista.conversas,
  analista.mensagens,
  analista.schema_chunks,
  analista.auditoria_sql
TO developer;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analista TO developer;
