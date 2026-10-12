import json
import os


def connect():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    try:
        import psycopg
    except ImportError:
        return None
    return psycopg.connect(url)


def ensure():
    conn = connect()
    if conn is None:
        return False
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS atlas_score (
              site_id text PRIMARY KEY,
              payload jsonb NOT NULL,
              updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    conn.close()
    return True


def save_score(site_id, payload):
    conn = connect()
    if conn is None:
        return False
    with conn:
        conn.execute(
            """
            INSERT INTO atlas_score (site_id, payload, updated_at)
            VALUES (%s, %s::jsonb, now())
            ON CONFLICT (site_id) DO UPDATE
            SET payload = EXCLUDED.payload, updated_at = now()
            """,
            (site_id, json.dumps(payload)),
        )
    conn.close()
    return True
