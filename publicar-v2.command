#!/bin/bash
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
rm -f .git/index.lock .git/HEAD.lock .git/ORIG_HEAD .git/MERGE_HEAD .git/CHERRY_PICK_HEAD .git/refs/heads/master.lock 2>/dev/null || true
git add \
  api/jobs.py \
  "api/jobs/[id].py" \
  src/lib/api.ts \
  src/app/jobs/page.tsx \
  src/app/leads/page.tsx \
  src/components/LeadModal.tsx
git commit -m "feat: quality filter, jobs clicáveis+deletáveis, contactos completos na tabela de leads"
git push origin master
echo "✅ Deploy enviado para o Vercel"
