-- ============================================================
-- PROSPECTOR BRAZA — Migration 001
-- Qualidade de Leads + Job FK
--
-- EXECUTAR NO: Supabase SQL Editor
-- URL: https://supabase.com/dashboard → teu projecto → SQL Editor
--
-- O QUE FAZ:
--   1. Adiciona job_id FK à tabela companies (corrige bug de delete)
--   2. Adiciona campos de qualidade ao lead (score 0-100, classificação)
--   3. Adiciona campos de confiança por campo (email, telefone)
--   4. Adiciona tracking de fontes e validação
--   5. Adiciona totais ao job (validos, descartados)
--   6. Cria índices para os novos campos
-- ============================================================

-- ─── 1. COMPANIES: job_id (FK) ────────────────────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS job_id UUID REFERENCES jobs(id) ON DELETE SET NULL;

COMMENT ON COLUMN companies.job_id IS
  'FK para o job que gerou este lead. Usado para delete correcto por job.';

-- ─── 2. COMPANIES: Score de qualidade 0-100 ──────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS score_qualidade_lead INTEGER DEFAULT 0;

COMMENT ON COLUMN companies.score_qualidade_lead IS
  'Score de qualidade do lead em escala 0-100. '
  'Excelente ≥ 60 | Bom ≥ 35 | Fraco ≥ 10 | Lixo < 10.';

-- ─── 3. COMPANIES: Classificação automática ───────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS classificacao_lead VARCHAR(20) DEFAULT 'pendente';

-- Constraint de valores válidos
ALTER TABLE companies
  DROP CONSTRAINT IF EXISTS check_classificacao_lead;
ALTER TABLE companies
  ADD CONSTRAINT check_classificacao_lead
  CHECK (classificacao_lead IN ('excelente', 'bom', 'fraco', 'lixo', 'pendente'));

COMMENT ON COLUMN companies.classificacao_lead IS
  'Classificação automática: excelente | bom | fraco | lixo | pendente';

-- ─── 4. COMPANIES: Motivo de descarte ────────────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS motivo_descarte TEXT;

COMMENT ON COLUMN companies.motivo_descarte IS
  'Razão pela qual o lead foi classificado como lixo ou fraco. Gerado automaticamente.';

-- ─── 5. COMPANIES: Confiança por campo ───────────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS confianca_email VARCHAR(20) DEFAULT 'desconhecida';

ALTER TABLE companies
  DROP CONSTRAINT IF EXISTS check_confianca_email;
ALTER TABLE companies
  ADD CONSTRAINT check_confianca_email
  CHECK (confianca_email IN ('alta', 'media', 'baixa', 'desconhecida'));

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS confianca_telefone VARCHAR(20) DEFAULT 'desconhecida';

ALTER TABLE companies
  DROP CONSTRAINT IF EXISTS check_confianca_telefone;
ALTER TABLE companies
  ADD CONSTRAINT check_confianca_telefone
  CHECK (confianca_telefone IN ('alta', 'media', 'baixa', 'desconhecida'));

COMMENT ON COLUMN companies.confianca_email IS
  'Confiança no email encontrado: alta (personalizado) | media (genérico) | baixa (junk)';
COMMENT ON COLUMN companies.confianca_telefone IS
  'Confiança no telefone: alta (API oficial) | media (extraído de HTML) | baixa | desconhecida';

-- ─── 6. COMPANIES: Fontes e validação ────────────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS fontes_encontradas TEXT[] DEFAULT ARRAY[]::TEXT[];

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS ultima_validacao TIMESTAMPTZ;

COMMENT ON COLUMN companies.fontes_encontradas IS
  'Array de fontes que encontraram este lead (ex: ["OSM Overpass", "Foursquare"])';
COMMENT ON COLUMN companies.ultima_validacao IS
  'Timestamp da última vez que os dados foram validados/enriquecidos.';

-- ─── 7. JOBS: Totais de qualidade ────────────────────────────────────────────

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS total_validos INTEGER DEFAULT 0;

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS total_descartados INTEGER DEFAULT 0;

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS logs_resumidos TEXT;

COMMENT ON COLUMN jobs.total_validos IS
  'Leads inseridos (classificação != lixo)';
COMMENT ON COLUMN jobs.total_descartados IS
  'Leads descartados automaticamente por classificação = lixo';
COMMENT ON COLUMN jobs.logs_resumidos IS
  'JSON com os últimos 50 logs de execução do job.';

-- ─── 8. ÍNDICES NOVOS ────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_companies_job_id
  ON companies(job_id);

CREATE INDEX IF NOT EXISTS idx_companies_classificacao
  ON companies(classificacao_lead);

CREATE INDEX IF NOT EXISTS idx_companies_score_qualidade
  ON companies(score_qualidade_lead DESC NULLS LAST);

-- Índice composto para os filtros mais comuns no dashboard
CREATE INDEX IF NOT EXISTS idx_companies_classif_score
  ON companies(classificacao_lead, score_qualidade_lead DESC NULLS LAST);

-- ─── 9. ACTUALIZAR LEADS EXISTENTES (retroactivo) ────────────────────────────
-- Classifica leads já existentes com base nos dados actuais.
-- ATENÇÃO: este UPDATE pode demorar se tiveres muitos leads.

UPDATE companies
SET
  classificacao_lead  = CASE
    WHEN (telefone IS NULL OR telefone = '')
     AND (email     IS NULL OR email    = '')
     AND (website   IS NULL OR website  = '')
     AND (instagram IS NULL OR instagram = '')
     AND (facebook  IS NULL OR facebook  = '')
    THEN 'lixo'
    WHEN score_prioridade_sdr >= 7 OR tem_website = TRUE AND (telefone IS NOT NULL AND telefone != '' OR email IS NOT NULL AND email != '')
    THEN 'excelente'
    WHEN telefone IS NOT NULL AND telefone != '' OR email IS NOT NULL AND email != ''
    THEN 'bom'
    ELSE 'fraco'
  END,
  score_qualidade_lead = CASE
    WHEN (telefone IS NULL OR telefone = '')
     AND (email     IS NULL OR email    = '')
     AND (website   IS NULL OR website  = '')
    THEN 0
    WHEN tem_website = TRUE AND (telefone IS NOT NULL AND telefone != '') AND (email IS NOT NULL AND email != '')
    THEN 70
    WHEN tem_website = TRUE AND ((telefone IS NOT NULL AND telefone != '') OR (email IS NOT NULL AND email != ''))
    THEN 50
    WHEN (telefone IS NOT NULL AND telefone != '') AND (email IS NOT NULL AND email != '')
    THEN 40
    WHEN (telefone IS NOT NULL AND telefone != '') OR (email IS NOT NULL AND email != '')
    THEN 25
    ELSE 10
  END
WHERE classificacao_lead = 'pendente' OR classificacao_lead IS NULL;

-- ─── VERIFICAÇÃO (correr depois para confirmar) ───────────────────────────────
-- SELECT classificacao_lead, COUNT(*) FROM companies GROUP BY classificacao_lead ORDER BY 2 DESC;
-- SELECT COUNT(*) FROM companies WHERE job_id IS NULL;
-- SELECT total_validos, total_descartados FROM jobs LIMIT 10;
