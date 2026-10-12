-- Atlas 0.1 — sistema de registro
-- Geometría en WGS84. Los snapshots de score no se actualizan.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE evidence (
  id uuid PRIMARY KEY,
  source_key text NOT NULL,
  title text NOT NULL,
  url text,
  citation text,
  retrieved_at timestamptz NOT NULL,
  license text,
  resolution text NOT NULL CHECK (resolution IN ('site', 'park', 'municipality', 'aquifer', 'region', 'national')),
  confidence text NOT NULL CHECK (confidence IN ('verified', 'estimated', 'proxy')),
  notes text
);

CREATE TABLE dataset_snapshot (
  id text PRIMARY KEY,
  source_key text NOT NULL,
  retrieved_at timestamptz NOT NULL,
  evidence_id uuid NOT NULL REFERENCES evidence (id)
);

CREATE TABLE corridor (
  id text PRIMARY KEY,
  name text NOT NULL,
  geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE municipality (
  cvegeo text PRIMARY KEY,
  name text NOT NULL,
  state_code text NOT NULL,
  geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE industrial_park (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  developer text,
  corridor_id text REFERENCES corridor (id),
  municipality_cvegeo text REFERENCES municipality (cvegeo),
  hectares numeric,
  available_hectares numeric,
  geom geometry(Geometry, 4326),
  geom_quality text NOT NULL CHECK (geom_quality IN ('polygon', 'point', 'missing')),
  evidence_id uuid REFERENCES evidence (id)
);

CREATE TABLE substation (
  id uuid PRIMARY KEY,
  name text,
  voltage_kv numeric,
  voltage_known boolean NOT NULL DEFAULT false,
  source text NOT NULL CHECK (source IN ('osm', 'manual')),
  suppressed boolean NOT NULL DEFAULT false,
  suppress_note text,
  geom geometry(Point, 4326) NOT NULL,
  evidence_id uuid REFERENCES evidence (id)
);

CREATE TABLE aquifer (
  id text PRIMARY KEY,
  name text NOT NULL,
  availability_hm3 numeric,
  status text NOT NULL CHECK (status IN ('deficit', 'equilibrium', 'surplus', 'unknown')),
  geom geometry(MultiPolygon, 4326),
  evidence_id uuid REFERENCES evidence (id)
);

CREATE TABLE portfolio (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  client_name text NOT NULL,
  corridor_id text NOT NULL REFERENCES corridor (id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE site (
  id uuid PRIMARY KEY,
  portfolio_id uuid NOT NULL REFERENCES portfolio (id),
  name text NOT NULL,
  park_id uuid REFERENCES industrial_park (id),
  corridor_id text NOT NULL REFERENCES corridor (id),
  municipality_cvegeo text REFERENCES municipality (cvegeo),
  status text NOT NULL CHECK (status IN ('candidate', 'shortlisted', 'rejected', 'operating')),
  geom geometry(Geometry, 4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE site_feature_snapshot (
  id uuid PRIMARY KEY,
  site_id uuid NOT NULL REFERENCES site (id),
  dataset_version text NOT NULL,
  computed_at timestamptz NOT NULL,
  features jsonb NOT NULL,
  UNIQUE (site_id, dataset_version)
);

CREATE TABLE scenario (
  id uuid PRIMARY KEY,
  portfolio_id uuid NOT NULL REFERENCES portfolio (id),
  name text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('load_mw', 'drought_year', 'corridor_delay')),
  params jsonb NOT NULL
);

CREATE TABLE score_snapshot (
  id uuid PRIMARY KEY,
  site_id uuid NOT NULL REFERENCES site (id),
  feature_snapshot_id uuid NOT NULL REFERENCES site_feature_snapshot (id),
  scenario_id uuid REFERENCES scenario (id),
  model_version text NOT NULL,
  weights jsonb NOT NULL,
  composite numeric,
  coverage numeric NOT NULL,
  publishable boolean NOT NULL,
  factors jsonb NOT NULL,
  computed_at timestamptz NOT NULL
);

CREATE TABLE analyst_note (
  id uuid PRIMARY KEY,
  site_id uuid NOT NULL REFERENCES site (id),
  body text NOT NULL,
  author text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE link (
  id uuid PRIMARY KEY,
  from_type text NOT NULL,
  from_id text NOT NULL,
  rel text NOT NULL,
  to_type text NOT NULL,
  to_id text NOT NULL,
  confidence text NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  props jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX site_geom_gix ON site USING gist (geom);
CREATE INDEX substation_geom_gix ON substation USING gist (geom);
CREATE INDEX municipality_geom_gix ON municipality USING gist (geom);
CREATE INDEX aquifer_geom_gix ON aquifer USING gist (geom);
CREATE INDEX score_site_idx ON score_snapshot (site_id, computed_at DESC);
