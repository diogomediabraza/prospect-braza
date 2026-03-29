-- ============================================================
-- Prospect Braza — Database Schema for Neon Postgres
-- Run once after creating your Neon project.
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Companies (Leads) ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS companies (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome                        VARCHAR(255) NOT NULL,
    nicho                       VARCHAR(100),
    localidade                  VARCHAR(100),
    morada                      VARCHAR(255),
    codigo_postal               VARCHAR(20),
    pais                        VARCHAR(50) DEFAULT 'Portugal',

    -- Contact
    telefone                    VARCHAR(50),
    telefone2                   VARCHAR(50),
    email                       VARCHAR(255),
    website                     VARCHAR(255),

    -- Social media
    facebook                    VARCHAR(255),
    instagram                   VARCHAR(255),
    linkedin                    VARCHAR(255),
    youtube                     VARCHAR(255),
    tiktok                      VARCHAR(255),

    -- Digital presence flags
    tem_website                 BOOLEAN DEFAULT FALSE,
    tem_loja_online             BOOLEAN DEFAULT FALSE,
    tem_facebook                BOOLEAN DEFAULT FALSE,
    tem_instagram               BOOLEAN DEFAULT FALSE,
    tem_linkedin                BOOLEAN DEFAULT FALSE,
    tem_youtube                 BOOLEAN DEFAULT FALSE,
    tem_tiktok                  BOOLEAN DEFAULT FALSE,

    -- Tracking & Ads
    tem_google_ads              BOOLEAN DEFAULT FALSE,
    tem_facebook_ads            BOOLEAN DEFAULT FALSE,
    tem_gtm                     BOOLEAN DEFAULT FALSE,
    tem_ga4                     BOOLEAN DEFAULT FALSE,
    tem_pixel_meta              BOOLEAN DEFAULT FALSE,

    -- AI Scores (0-10)
    score_maturidade_digital    DECIMAL(4,1),
    score_oportunidade_comercial DECIMAL(4,1),
    score_prioridade_sdr        DECIMAL(4,1),

    -- CRM
    status                      VARCHAR(20) DEFAULT 'novo'
                                CHECK (status IN ('novo','abordado','em_negociacao','fechado','descartado','nao_contactar')),
    notas                       TEXT,

    -- Metadata
    fonte                       VARCHAR(100),
    data_criacao                TIMESTAMPTZ DEFAULT NOW(),
    data_atualizacao            TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate leads
    UNIQUE (nome, localidade)
);

-- Indexes for frequent queries
CREATE INDEX IF NOT EXISTS idx_companies_status     ON companies(status);
CREATE INDEX IF NOT EXISTS idx_companies_nicho      ON companies(nicho);
CREATE INDEX IF NOT EXISTS idx_companies_localidade ON companies(localidade);
CREATE INDEX IF NOT EXISTS idx_companies_score_sdr  ON companies(score_prioridade_sdr DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_companies_score_op   ON companies(score_oportunidade_comercial DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_companies_criacao    ON companies(data_criacao DESC);

-- Full text search
CREATE INDEX IF NOT EXISTS idx_companies_fts ON companies
    USING gin(to_tsvector('portuguese', nome || ' ' || COALESCE(nicho,'') || ' ' || COALESCE(localidade,'')));

-- ─── Jobs ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jobs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nicho               VARCHAR(100) NOT NULL,
    localidade          VARCHAR(100) NOT NULL,
    max_resultados      INTEGER DEFAULT 50,
    status              VARCHAR(20) DEFAULT 'pendente'
                        CHECK (status IN ('pendente','a_correr','concluido','erro','cancelado')),
    progresso           INTEGER DEFAULT 0 CHECK (progresso BETWEEN 0 AND 100),
    total_encontrados   INTEGER DEFAULT 0,
    mensagem_erro       TEXT,
    data_inicio         TIMESTAMPTZ DEFAULT NOW(),
    data_fim            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_status     ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_data       ON jobs(data_inicio DESC);

-- ─── Auto-update data_atualizacao trigger ──────────────────────

CREATE OR REPLACE FUNCTION update_atualizacao()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_atualizacao = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_companies_atualizacao ON companies;
CREATE TRIGGER trigger_companies_atualizacao
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_atualizacao();
