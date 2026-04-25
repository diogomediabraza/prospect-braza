#!/bin/bash
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "🔒 A remover lock files..."
find .git -name "*.lock" -delete 2>/dev/null || true
find .git -name "*.lock.bak*" -delete 2>/dev/null || true

echo "📝 A fazer commit..."
git add api/jobs.py
git commit -m "feat: só guardar leads bom/excelente (score≥35) — fraco e lixo descartados, busca 4x pool"

echo "⬆️  A fazer push..."
git push origin master

echo ""
echo "✅ Concluído!"
git log --oneline -3
read -p "Pressiona Enter para fechar..."
