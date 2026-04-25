#!/bin/bash
cd "$(dirname "$0")"

# Remove qualquer lock file pendente
rm -f .git/index.lock
rm -f .git/HEAD.lock
rm -f .git/refs/heads/master.lock

# Configurar credential helper para usar o keychain do macOS
git config credential.helper osxkeychain

# Fazer o commit
git add api/lib/scraper.py api/jobs.py
git commit -m "feat: enriquecimento automatico - extrai email e telefone do website"

# Push usando as credenciais armazenadas pelo GitHub Desktop
git push origin master

echo "---"
echo "DONE. Pode fechar esta janela."
read
