#!/bin/sh
# Lo mismo que .github/workflows/ci.yml, para correr sin GitHub Actions (D-015).
# Uso: sh herramientas/verificar.sh   (desde la raíz del repo)
set -eu
cd "$(dirname "$0")/.."

echo "== lint"
ruff check .

echo "== pytest con cobertura (el piso es el mismo del CI)"
piso=$(sed -n 's/.*--cov-fail-under=\([0-9]*\).*/\1/p' .github/workflows/ci.yml | head -1)
python3 -m pytest -q --cov --cov-report=term --cov-fail-under="$piso"
rm -f .coverage

echo "== score de escritorio"
node --test packages/score/score.test.mjs

echo "== smoke import del API"
(cd services/api && python3 -c "import atlas.score, atlas.main, atlas.access, atlas.oracle")

echo "== docker-compose válido"
if command -v docker >/dev/null 2>&1; then
  docker compose config -q
else
  echo "(sin docker en esta máquina: se salta)"
fi

echo "== todo en verde"
