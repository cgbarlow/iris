"""PostgreSQL migration runner for Supabase deployment mode."""
from __future__ import annotations
import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import asyncpg

async def run_supabase_migrations(pool: asyncpg.Pool) -> None:
    """Run all PostgreSQL migrations idempotently."""
    migrations_dir = os.path.dirname(__file__)
    sql_files = sorted(
        f for f in os.listdir(migrations_dir)
        if f.endswith('.sql') and not f.startswith('_')
    )
    async with pool.acquire() as conn:
        for sql_file in sql_files:
            sql_path = os.path.join(migrations_dir, sql_file)
            with open(sql_path) as f:
                sql = f.read().strip()
            if sql:
                await conn.execute(sql)
