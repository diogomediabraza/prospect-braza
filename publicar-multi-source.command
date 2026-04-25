#!/bin/bash
# Publicar: multi-source scraper (Wikidata, Foursquare, HERE, Google Places, Infopaginas, GuiaEmpresa)
# Executar com duplo-clique no Finder

set -e

# Navega para a pasta do repositório (onde este script está)
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
echo "Repositório: $REPO"

# Remover ficheiros de lock do git (iCloud Drive pode deixar estes ficheiros bloqueados)
rm -f .git/index.lock .git/HEAD.lock .git/ORIG_HEAD .git/MERGE_HEAD .git/CHERRY_PICK_HEAD .git/refs/heads/master.lock 2>/dev/null || true
echo "Lock files removidos."

# Adicionar todos os ficheiros novos e modificados
git add api/lib/scraper.py
git add api/jobs.py
git add api/lib/source_wikidata.py
git add api/lib/source_infopaginas.py
git add api/lib/source_apis.py

# Commit
git commit -m "feat: multi-source scraper — Wikidata, Foursquare, HERE, Google Places, infopaginas, GuiaEmpresa + OSM deduplication"

# Push para GitHub (trigger Vercel deploy)
git push origin master

echo ""
echo "✅ Deploy iniciado! Aguarda ~1 minuto e testa no Vercel."
read -p "Pressiona Enter para fechar..."
