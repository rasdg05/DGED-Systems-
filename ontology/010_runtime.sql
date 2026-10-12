CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS atlas_score (
  site_id text PRIMARY KEY,
  payload jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS atlas_site (
  id text PRIMARY KEY,
  name text NOT NULL,
  corridor text NOT NULL,
  note text,
  geom geometry(Point, 4326) NOT NULL
);
