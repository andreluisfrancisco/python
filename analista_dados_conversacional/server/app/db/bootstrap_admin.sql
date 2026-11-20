-- Rode como superusuário, conectado no database app.
-- A extensão vector fica no schema public e serve a todos os projetos.
-- O schema analista é criado depois, pelo papel migration.

CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analista_leitura') THEN
    CREATE ROLE analista_leitura NOLOGIN;
  END IF;
END
$$;

GRANT analista_leitura TO developer;
