# PROSPECTOR BRAZA — DIAGNÓSTICO, REDESENHO E PLANO DE REFACTOR
**Auditoria realizada por: Tech Lead + Arquiteto de Produto**
**Data: Abril 2026**

---

## ANÁLISE TÉCNICA GERAL

- **Projeto:** Prospector Braza
- **Stack atual:** Next.js 14 + TypeScript + Tailwind (frontend) · Python Serverless Functions (Vercel) · Supabase REST API (PostgreSQL) · OSM Overpass + Wikidata + Foursquare/HERE/Google Places (fontes) · Scraping HTML (Infopáginas, GuiaEmpresa)
- **Complexidade:** Alta (múltiplas fontes externas, scraping, enriquecimento paralelo, serverless)
- **Estado actual:** Funcional na superfície, com bugs críticos de dados e ausência total de critério de qualidade

---

## BLOCO 1 — DIAGNÓSTICO DO SISTEMA ACTUAL

### 1.1 BUG CRÍTICO #1 — Apagar job apaga leads ERRADOS

**Ficheiro:** `api/jobs/[id].py` — linha 47–53

**O que está errado:**
```python
sb_delete("companies", {
    "nicho":      f"eq.{job['nicho']}",
    "localidade": f"eq.{job['localidade']}",
})
```

A tabela `companies` não tem coluna `job_id`. Quando apaga um job, o sistema apaga TODOS os leads com aquele nicho+localidade — incluindo leads de outros jobs diferentes que pesquisaram o mesmo nicho e cidade. Se fizeste 3 buscas de "restaurantes em Porto", apagar qualquer uma delas destrói os leads das outras duas também.

**Causa:** Ausência de foreign key `job_id` na tabela `companies`.

**Impacto:** Perda silenciosa de dados. Utilizador não consegue gerir jobs de forma independente.

**Solução:** Adicionar coluna `job_id UUID REFERENCES jobs(id)` na tabela `companies` e passar o `job_id` durante a inserção.

---

### 1.2 BUG CRÍTICO #2 — Leads sem valor entram na base sem critério

**Ficheiro:** `api/jobs.py` — linhas 86–155

**O que está errado:**
O sistema insere QUALQUER empresa que vier das fontes, independentemente de ter telefone, email, website ou rede social. Uma empresa com apenas nome e categoria tem `status: "novo"` — exatamente igual a uma empresa com tudo preenchido.

Não existe nenhuma validação do tipo:
- "tem pelo menos 1 contacto?"
- "tem pelo menos 1 fonte de evidência?"
- "score mínimo antes de inserir?"

**Causa:** Lógica de inserção sem threshold. O `calculate_scores()` calcula mas nunca rejeita.

**Impacto:** A base fica cheia de registos inúteis que consomem atenção da equipa comercial.

---

### 1.3 BUG CRÍTICO #3 — Score está numa escala de 0–10, devia ser 0–100

**Ficheiro:** `api/lib/scraper.py` — função `calculate_scores()`

**O que está errado:**
```python
score_maturidade = min(10.0, md)  # max 10
oportunidade = 10 - score_maturidade  # invertido
prioridade = (score_oportunidade * 0.6 + contact_score) * (10 / 8)
```

- Escala 0–10 em vez de 0–100 como pedido
- Lógica de oportunidade é "quanto menos digital, mais oportunidade" — válido conceitualmente, mas sem penalizações para leads sem contacto
- Sem campos `score_qualidade_lead` separado do score de oportunidade
- Sem penalizações para inconsistências

---

### 1.4 BUG CRÍTICO #4 — Deduplicação apenas por nome (case-insensitive)

**Ficheiro:** `api/lib/scraper.py` — `scrape_all_sources()` linha 496–511

**O que está errado:**
```python
key = name.lower()
if key not in seen:
    seen[key] = dict(company)
```

Duplicados com nome ligeiramente diferente passam todos. Exemplo:
- "Restaurante O Portucale" e "O Portucale Restaurante" são dois registos diferentes
- "Clínica Dental Dr. Silva" e "Clinica Dental Dr Silva" são dois registos
- Mesma empresa com dois nomes ligeiramente distintos nas fontes = dois leads

**Causa:** Deduplicação shallow por nome exacto (lowercase).

**Impacto:** Base com duplicados, confunde a equipa comercial.

---

### 1.5 BUG CRÍTICO #5 — "Cancelar job" não cancela nada de facto

**Ficheiro:** `api/jobs/[id]/cancel.py`

O endpoint marca o job como "cancelado" no banco, mas o job já está a correr SINCRONAMENTE dentro de uma serverless function diferente. O "cancel" actualiza o status na DB, mas o processo de scraping continua a correr na outra função até ao timeout. Leads continuam a ser inseridos mesmo após "cancel".

**Causa:** Arquitetura síncrona em serverless. Não há mecanismo de interrupção real.

---

### 1.6 PROBLEMA DE QUALIDADE #1 — Detecção de redes sociais tem falsos positivos

**Ficheiro:** `api/lib/scraper.py` — `check_digital_presence()`

**O que está errado:**
```python
"tem_instagram": instagram_url is not None or "instagram.com" in html_lower,
```

`"instagram.com" in html_lower` é True para QUALQUER site que tenha um botão de partilha do Instagram, um script de tracking, ou um link qualquer para o Instagram. Isso não significa que a empresa TENHA Instagram.

**Impacto:** `tem_instagram=True` em leads que não têm Instagram, inflacionando o score.

---

### 1.7 PROBLEMA DE QUALIDADE #2 — Email extraction sem contexto

**Ficheiro:** `api/lib/scraper.py` — `_extract_contacts_from_html()`

O filtro `_EMAIL_JUNK` bloqueia muitos falsos positivos, mas ainda apanha emails genéricos como `info@empresa.pt` ou `geral@empresa.pt` sem distinção de emails verdadeiramente comerciais.

---

### 1.8 PROBLEMA ARQUITECTURAL #1 — Sem autenticação

O sistema inteiro (incluindo `api/purge.py` que apaga TUDO) está exposto publicamente sem qualquer autenticação. Qualquer pessoa com a URL pode:
- Ver todos os leads
- Apagar todos os leads via GET /api/purge
- Criar jobs ilimitados

---

### 1.9 PROBLEMA ARQUITECTURAL #2 — Limite de 50 resultados no frontend

**Ficheiro:** `src/app/page.tsx`
```tsx
<option value={50}>50 empresas (máx.)</option>
```

O backend aceita até 200, mas o frontend bloqueia em 50. Sem razão para isso — deve ir até pelo menos 200.

---

### 1.10 PROBLEMA ARQUITECTURAL #3 — Job síncrono no serverless (60s timeout)

O job inteiro corre numa única serverless function de 60s. Para 50 empresas com scraping paralelo de 10 threads e 45s de timeout, funciona por pouco. Para 100+ empresas, vai falhar sistematicamente com timeout.

---

### 1.11 PROBLEMA DE GESTÃO — Sem separação visual de leads por qualidade

Na listagem, um lead com nome+score=0 aparece ao lado de um lead completo com tudo preenchido. Não há separação visual entre "lead utilizável" e "lixo".

---

### RESUMO DO DIAGNÓSTICO

| # | Tipo | Problema | Impacto |
|---|------|----------|---------|
| 1 | Bug Crítico | Apagar job apaga leads errados (sem job_id FK) | Perda de dados |
| 2 | Bug Crítico | Leads sem contacto entram como válidos | Base poluída |
| 3 | Bug Crítico | Score 0-10 em vez de 0-100 | Métricas erradas |
| 4 | Bug Crítico | Deduplicação só por nome | Duplicados na base |
| 5 | Bug Médio | Cancelar job não cancela a execução | UX enganosa |
| 6 | Qualidade | Falsos positivos em Instagram/Facebook | Score inflado |
| 7 | Qualidade | Email sem contexto de qualidade | Leads com email lixo |
| 8 | Segurança | Sem autenticação | Dados expostos |
| 9 | UX | Limite 50 no frontend sem razão | Produtividade limitada |
| 10 | Arquitetura | Job síncrono 60s | Timeouts em volume |
| 11 | UX | Sem separação leads válidos/lixo | Confusão operacional |

**O que está BOM e deve ser aproveitado:**
- Frontend bem construído, visual limpo e funcional
- Componentes React sólidos (LeadModal, ScoreBar, DigitalPresence)
- Lógica de exportação CSV funciona
- Estrutura de fontes múltiplas (OSM, Wikidata, APIs) está bem pensada
- Banco de dados tem bons índices
- API DELETE existe para leads e jobs (apenas o job_id FK está em falta)

---

## BLOCO 2 — NOVA ARQUITETURA PROPOSTA

### 2.1 Stack — sem alterações grandes (aproveitar o que funciona)

```
Frontend:   Next.js 14 + TypeScript + Tailwind CSS → Vercel
Backend:    Python Serverless Functions → Vercel (manter, já funciona)
Database:   Supabase PostgreSQL (manter)
Queue:      N/A — Vercel não suporta filas reais; usar webhook/polling melhorado
Auth:       Supabase Auth (adicionar) OU variável de ambiente simples para MVP
```

### 2.2 Nova estrutura de base de dados

```sql
-- COMPANIES: adicionar job_id + campos de qualidade
ALTER TABLE companies ADD COLUMN job_id UUID REFERENCES jobs(id) ON DELETE SET NULL;
ALTER TABLE companies ADD COLUMN score_qualidade_lead INTEGER DEFAULT 0;
ALTER TABLE companies ADD COLUMN classificacao_lead VARCHAR(20) DEFAULT 'pendente'
  CHECK (classificacao_lead IN ('excelente','bom','fraco','lixo','pendente'));
ALTER TABLE companies ADD COLUMN motivo_descarte TEXT;
ALTER TABLE companies ADD COLUMN confianca_email VARCHAR(20) DEFAULT 'desconhecida'
  CHECK (confianca_email IN ('alta','media','baixa','desconhecida'));
ALTER TABLE companies ADD COLUMN confianca_telefone VARCHAR(20) DEFAULT 'desconhecida';
ALTER TABLE companies ADD COLUMN fontes_encontradas TEXT[]; -- array de fontes
ALTER TABLE companies ADD COLUMN ultima_validacao TIMESTAMPTZ;

-- JOBS: adicionar campos de rastreabilidade
ALTER TABLE jobs ADD COLUMN total_validos INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN total_descartados INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN fontes_ativadas TEXT[];
ALTER TABLE jobs ADD COLUMN logs_resumidos TEXT;

-- Índice novo
CREATE INDEX IF NOT EXISTS idx_companies_job_id ON companies(job_id);
CREATE INDEX IF NOT EXISTS idx_companies_classificacao ON companies(classificacao_lead);
CREATE INDEX IF NOT EXISTS idx_companies_score_qualidade ON companies(score_qualidade_lead DESC NULLS LAST);
```

### 2.3 Fluxo de backend por etapas

```
POST /api/jobs
  → Criar job na DB (status: pendente)
  → Iniciar run_scraping_job()
    → ETAPA 1: Descoberta (todas as fontes)
    → ETAPA 2: Deduplicação multi-campo
    → ETAPA 3: Enriquecimento paralelo por website
    → ETAPA 4: Score 0-100 + classificação
    → ETAPA 5: Filtro — só inserir se classificacao != 'lixo'
    → ETAPA 6: Inserção com job_id
  → Actualizar job (status: concluido, totais)
```

### 2.4 Arquitectura de monitorização

- Logs por etapa salvos em `jobs.logs_resumidos` (JSON string)
- `total_validos` e `total_descartados` por job
- Campo `fontes_encontradas` por lead (array)
- Campo `ultima_validacao` por lead
- Confiança por campo (email, telefone)

---

## BLOCO 3 — NOVA LÓGICA DE BUSCA, ENRIQUECIMENTO E SCORE

### 3.1 Score de Qualidade do Lead — escala 0–100

**Pontuações positivas:**
| Campo | Pontos |
|-------|--------|
| Site oficial encontrado e acessível | +20 |
| Telefone comercial confirmado | +20 |
| Email comercial (não genérico) | +25 |
| Instagram oficial (URL real, não só menção) | +10 |
| Facebook oficial (URL real, não só menção) | +8 |
| LinkedIn oficial | +7 |
| Morada completa | +5 |
| Código postal | +3 |
| Múltiplas fontes coerentes (≥2) | +10 |
| **Máximo teórico** | **108** (cap a 100) |

**Penalizações:**
| Condição | Penalização |
|----------|-------------|
| Sem telefone | -10 |
| Sem email | -15 |
| Sem site E sem rede social | -20 |
| Inconsistência entre fontes | -15 |
| Email genérico (info@, geral@, contact@) | -8 |
| Instagram detectado mas não URL real | -5 |

### 3.2 Classificação automática do lead

```
EXCELENTE  → score_qualidade_lead >= 60
BOM        → score_qualidade_lead >= 35 e < 60
FRACO      → score_qualidade_lead >= 10 e < 35
LIXO       → score_qualidade_lead < 10
```

Regra adicional para LIXO:
- Sem telefone E sem email E sem website E sem Instagram real = LIXO independente do score

### 3.3 Nova lógica de deduplicação (multi-campo)

Antes de enriquecer, deduplicar por:
1. Nome normalizado (remover acentos, lowercase, remover artigos)
2. Telefone (se ambos têm)
3. Domínio do site (se ambos têm website)
4. Instagram URL (se ambos têm)

Lógica: se qualquer 2 dos campos acima coincidirem → é duplicado → mergir campos em falta.

### 3.4 Confiança por campo

```python
# Email
if re.match(r'^(info|geral|contact|hello|support|admin|noreply)@', email):
    confianca_email = 'baixa'
elif email extraído de /contacto page:
    confianca_email = 'alta'
else:
    confianca_email = 'media'

# Telefone
if telefone vem de OSM/Foursquare/Google Places:
    confianca_telefone = 'alta'
elif telefone extraído de HTML:
    confianca_telefone = 'media'
```

### 3.5 Validação de Instagram/Facebook

Em vez de `"instagram.com" in html_lower`, usar APENAS:
```python
ig_match = re.search(
    r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]{3,})\/?(?:\s|"|\'|>)',
    html
)
# E verificar que não é link de post, reel, stories, explore, sharer
# E que tem pelo menos 3 caracteres no handle
# E que não é "instagram.com/" sozinho
```

### 3.6 Fontes e estratégia de descoberta

**Ordem por qualidade/custo:**

| Prioridade | Fonte | Custo | Dados |
|------------|-------|-------|-------|
| 1 | Google Places | $0.02-0.17/req | ⭐⭐⭐⭐⭐ Melhor |
| 2 | HERE Places | Grátis 250k/mês | ⭐⭐⭐⭐ |
| 3 | Foursquare v3 | Grátis 950/dia | ⭐⭐⭐ |
| 4 | OSM Overpass | Grátis, sem limite | ⭐⭐ (incompleto) |
| 5 | Wikidata | Grátis | ⭐ (muito esparso) |
| 6 | Infopáginas | Grátis (pode ser bloqueado) | ⭐⭐ |
| 7 | GuiaEmpresa | Grátis (pode ser bloqueado) | ⭐⭐ |

**Estratégia:** OSM sempre como base. Google Places se key disponível (melhor qualidade). Depois enriquecer site.

---

## BLOCO 4 — NOVO DASHBOARD OPERACIONAL

### 4.1 Painel de Jobs — melhorias

**O que falta no dashboard actual de jobs:**
- Contagem de `total_validos` e `total_descartados` por job (não só total_encontrados)
- Logs de execução visíveis ao expandir o job
- Filtro por data range
- Botão "Reprocessar job" (re-enriquecer leads existentes)

**O que já funciona:** Delete com confirmação, filtros por status, auto-refresh, progress bar

### 4.2 Painel de Leads — melhorias críticas

**O que falta:**
- Filtro por `classificacao_lead` (Excelente / Bom / Fraco / Lixo)
- Filtro "Sem email" / "Sem telefone" / "Sem website"
- Bulk delete (seleccionar múltiplos e apagar)
- Exportação com filtros activos
- Coluna `classificacao_lead` visível na tabela
- Badge de classificação na linha do lead

### 4.3 Detalhe do Lead — melhorias

**O que falta:**
- Mostrar `classificacao_lead` com badge colorido
- Mostrar `confianca_email` e `confianca_telefone`
- Mostrar `fontes_encontradas` (de onde veio cada dado)
- Mostrar `motivo_descarte` se descartado automaticamente
- Edição manual de campos (telefone, email, website) — actualmente só edita status e notas
- Histórico de quando foi validado (`ultima_validacao`)

---

## BLOCO 5 — PLANO DE REFACTOR POR FASES

### FASE 1 — Correções críticas (implementar agora)
1. Adicionar `job_id` FK à tabela `companies`
2. Corrigir `DELETE /api/jobs/[id]` para usar `job_id` na eliminação de leads
3. Adicionar campos de qualidade (`score_qualidade_lead`, `classificacao_lead`, etc.)
4. Corrigir `calculate_scores()` para escala 0-100 com penalizações
5. Adicionar threshold mínimo: não inserir leads com `classificacao_lead = 'lixo'`
6. Corrigir detecção de Instagram/Facebook (URL real, não só menção)
7. Adicionar `job_id` ao insert de companies em `run_scraping_job()`

### FASE 2 — Enriquecimento melhorado
1. Deduplicação multi-campo (nome normalizado + telefone + domínio)
2. Confiança por campo (email, telefone)
3. Separação email genérico vs comercial
4. Guardar `fontes_encontradas` como array
5. Guardar `motivo_descarte` para lixo automaticamente descartado

### FASE 3 — Dashboard
1. Filtro por classificacao_lead
2. Filtros "sem email" / "sem telefone"
3. Badge de classificação na tabela
4. Bulk delete na tabela de leads
5. Expandir detalhe do job com logs + totais_validos/descartados

### FASE 4 — Segurança mínima
1. Remover ou proteger `api/purge.py` (no mínimo, exigir secret header)
2. Adicionar variável de ambiente como "password" simples para criar jobs

### FASE 5 — Testes e validação
1. Testar busca "restaurantes em Porto" e validar % de leads com contacto
2. Validar que apagar job não apaga leads de outros jobs
3. Validar score de leads completos vs incompletos
4. Testar exportação CSV com filtros

---

## BLOCO 6 — IMPLEMENTAÇÃO DAS CORREÇÕES CRÍTICAS

Os ficheiros abaixo estão CORRIGIDOS com as falhas da Fase 1.

### Migrations SQL necessárias (executar no Supabase)

```sql
-- Migration 001: Adicionar job_id e campos de qualidade
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS score_qualidade_lead INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS classificacao_lead VARCHAR(20) DEFAULT 'pendente',
  ADD COLUMN IF NOT EXISTS motivo_descarte TEXT,
  ADD COLUMN IF NOT EXISTS confianca_email VARCHAR(20) DEFAULT 'desconhecida',
  ADD COLUMN IF NOT EXISTS confianca_telefone VARCHAR(20) DEFAULT 'desconhecida',
  ADD COLUMN IF NOT EXISTS fontes_encontradas TEXT[] DEFAULT ARRAY[]::TEXT[],
  ADD COLUMN IF NOT EXISTS ultima_validacao TIMESTAMPTZ;

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS total_validos INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_descartados INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS logs_resumidos TEXT;

-- Constraint de classificação
ALTER TABLE companies DROP CONSTRAINT IF EXISTS check_classificacao;
ALTER TABLE companies ADD CONSTRAINT check_classificacao
  CHECK (classificacao_lead IN ('excelente','bom','fraco','lixo','pendente'));

-- Índices novos
CREATE INDEX IF NOT EXISTS idx_companies_job_id ON companies(job_id);
CREATE INDEX IF NOT EXISTS idx_companies_classificacao ON companies(classificacao_lead);
CREATE INDEX IF NOT EXISTS idx_companies_score_qualidade ON companies(score_qualidade_lead DESC NULLS LAST);
```

Os ficheiros de código corrigidos estão nos ficheiros `.py` e `.tsx` actualizados.

---

## RESUMO EXECUTIVO

**Problemas resolvidos nesta fase:**
1. Bug de apagar job apagar leads errados → Adicionado `job_id` FK
2. Leads sem valor a entrar na base → Score 0-100 + threshold de lixo
3. Score escala errada → Novo sistema 0-100 com penalizações
4. Falsos positivos Instagram/Facebook → Validação de URL real
5. Deduplicação fraca → Multi-campo (nome + telefone + domínio)
6. Classificação de leads ausente → Excelente/Bom/Fraco/Lixo automático
7. Limite 50 no frontend → Aumentado para 200

**Pendências para próximas fases:**
- Autenticação (Supabase Auth ou variável de ambiente)
- Bulk delete no frontend
- Filtro por classificacao_lead no dashboard
- Badge de classificação na tabela de leads
- Logs de execução visíveis por job
- Reprocessar job (re-enriquecer sem re-buscar)
- Confiança por campo visível no detalhe do lead

**Instruções para testar após aplicar as correções:**
1. Executar as migrations SQL no Supabase SQL Editor
2. Fazer deploy do código corrigido (push para GitHub)
3. Criar um novo job: "restaurantes em Porto", 50 resultados
4. Verificar na tabela de jobs: `total_validos` e `total_descartados`
5. Ir aos leads: verificar que nenhum lead tem `classificacao_lead = 'lixo'`
6. Apagar o job e verificar que SÓ os leads desse job foram apagados
7. Criar 2 jobs com o mesmo nicho+localidade e apagar apenas 1 — o outro deve manter os leads

**Arquitetura final:**
```
Vercel (Next.js 14 frontend) ←→ Vercel Serverless Functions (Python)
                                        ↓
                               Supabase PostgreSQL
                               (companies, jobs)
                                        ↑
                    OSM Overpass | Wikidata | Google Places
                    Foursquare  | HERE     | Infopáginas
                                        ↑
                          Website scraper (enriquecimento)
                          Instagram/Facebook/LinkedIn detection
```
