#!/usr/bin/env bash
# Prepara o database app no Postgres único da máquina (127.0.0.1:5432).
# Instala o pgvector no container postgres-db, se a imagem ainda não tiver o pacote.
# Cria a extensão no schema public e o papel analista_leitura.
# Não cria outro database nem outro container.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${POSTGRES_CONTAINER:-postgres-db}"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Container ${CONTAINER} não está na máquina. Suba o Postgres de database/postgres." >&2
  exit 1
fi

docker exec -u root "$CONTAINER" bash -c 'dpkg -s postgresql-18-pgvector >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y postgresql-18-pgvector; }'

docker exec -i "$CONTAINER" psql -U admin -d app -v ON_ERROR_STOP=1 < "$ROOT/app/db/bootstrap_admin.sql"

echo "Database app pronto em 127.0.0.1:5432. O schema analista entra no próximo passo."
echo "Próximo passo: python scripts/init_db.py"
