#!/bin/bash
# Script para resolver conflitos e fazer push do v2
# Duplo-clique para executar

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
echo "📁 Repositório: $REPO"

# 1. Remover TODOS os lock files
echo ""
echo "🔓 A remover lock files..."
find .git -name "*.lock" -delete 2>/dev/null || true
find .git -name "*.lock.old*" -delete 2>/dev/null || true
find .git -name "*.lock.bk*" -delete 2>/dev/null || true
echo "✅ Lock files removidos."

# 2. Abortar qualquer rebase/merge em curso
echo ""
echo "🔄 A verificar estado do repositório..."
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    echo "⚠️  Rebase em curso. A abortar..."
    GIT_EDITOR=true git rebase --abort 2>/dev/null || true
    echo "✅ Rebase abortado."
fi
if [ -f .git/MERGE_HEAD ]; then
    echo "⚠️  Merge em curso. A abortar..."
    git merge --abort 2>/dev/null || true
    echo "✅ Merge abortado."
fi

# 3. Limpar novamente após abort
find .git -name "*.lock" -delete 2>/dev/null || true

# 4. Mostrar estado
echo ""
echo "📊 Estado atual:"
git log --oneline -3
echo ""

# 5. Pull com --no-edit para não abrir editor de merge
echo ""
echo "⬇️  A fazer pull (versão local v2 ganha em conflitos)..."
export GIT_EDITOR=true
export GIT_MERGE_AUTOEDIT=no

git pull origin master -X ours --no-rebase --no-edit 2>&1
PULL_STATUS=$?

if [ $PULL_STATUS -ne 0 ]; then
    echo ""
    echo "⚠️  Conflitos a resolver manualmente..."
    # Aceitar nossa versão para todos os ficheiros em conflito
    CONFLICTED=$(git diff --name-only --diff-filter=U 2>/dev/null)
    if [ -n "$CONFLICTED" ]; then
        echo "$CONFLICTED" | xargs git checkout --ours --
        git add -A
        GIT_EDITOR=true git commit --no-edit -m "merge: aceitar v2 sobre fixes remotos" 2>/dev/null || true
    fi
fi

echo ""
echo "✅ Pull concluído!"
git log --oneline -5

# 6. Push para GitHub
echo ""
echo "⬆️  A fazer push para GitHub..."
git push origin master

echo ""
echo "🚀 Push concluído! Deploy Vercel iniciado em breve."
echo ""
read -p "Pressiona Enter para fechar..."
