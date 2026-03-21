#!/usr/bin/env bash
# Run all Supabase migrations against a PostgreSQL database.
#
# Usage:
#   ./scripts/supabase-migrate.sh <SUPABASE_DB_URL>
#
# Example:
#   ./scripts/supabase-migrate.sh "postgresql://postgres:MyPassword@db.xxxx.supabase.co:5432/postgres"
#
# Uses the DIRECT connection (port 5432), not the Transaction pooler,
# because migrations use DDL and may need prepared statements.
# The Transaction pooler (port 6543) is for the runtime app only.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <DATABASE_URL>"
    echo ""
    echo "Example:"
    echo "  $0 \"postgresql://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres\""
    exit 1
fi

DB_URL="$1"
MIGRATIONS_DIR="$(cd "$(dirname "$0")/../backend/app/migrations/supabase" && pwd)"

echo "Running Supabase migrations from: $MIGRATIONS_DIR"
echo ""

for file in "$MIGRATIONS_DIR"/m*.sql; do
    name=$(basename "$file")
    echo "  Running $name ..."
    psql "$DB_URL" -f "$file" -v ON_ERROR_STOP=1 --quiet
done

echo ""
echo "All migrations applied successfully."
