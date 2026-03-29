# Prospect Braza

**Motor de Prospecção B2B** — by We Braza Group

Encontra empresas B2B, analisa a maturidade digital e prioriza os melhores leads para o teu SDR.

---

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend:** Python Serverless Functions (Vercel)
- **Database:** Neon Postgres (serverless PostgreSQL)
- **Scraping:** Páginas Amarelas (Portugal)

---

## Deploy Rápido

### 1. Base de dados (Neon)

1. Cria uma conta em [neon.tech](https://neon.tech)
2. Cria um novo projecto
3. Copia o **Connection String**
4. Corre o schema: `psql "$DATABASE_URL" -f schema.sql`

### 2. Deploy no Vercel

1. Faz fork do repositório
2. Vai a [vercel.com](https://vercel.com) → "New Project"
3. Importa o repositório
4. Adiciona a variável de ambiente:
   - `DATABASE_URL` = a tua connection string do Neon
5. Clica em **Deploy**

---

## Desenvolvimento Local

```bash
# Instalar dependências
npm install

# Copiar env
cp .env.example .env.local
# Preencher DATABASE_URL em .env.local

# Correr em desenvolvimento
npm run dev
```

---

## Estrutura do Projecto

```
prospect-braza/
├── src/
│   ├── app/              # Next.js App Router pages
│   │   ├── page.tsx      # Dashboard
│   │   ├── leads/        # Base de leads
│   │   ├── jobs/         # Jobs de pesquisa
│   │   └── export/       # Exportar CSV
│   ├── components/       # Componentes React
│   └── lib/              # API client + tipos
├── api/                  # Python serverless functions
│   ├── leads.py          # GET /api/leads
│   ├── leads/[id].py     # GET/PATCH/DELETE /api/leads/:id
│   ├── leads/export.py   # GET /api/leads/export
│   ├── jobs.py           # GET/POST /api/jobs
│   ├── jobs/[id].py      # GET /api/jobs/:id
│   ├── jobs/[id]/cancel.py  # POST /api/jobs/:id/cancel
│   ├── stats.py          # GET /api/stats
│   └── lib/              # Utilitários partilhados
├── schema.sql            # Schema da base de dados
└── vercel.json           # Configuração Vercel
```

---

*Powered by We Braza Group · [mediabraza.com](https://mediabraza.com)*
