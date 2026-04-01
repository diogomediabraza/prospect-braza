export type CompanyStatus =
  | "novo"
  | "abordado"
  | "em_negociacao"
  | "fechado"
  | "descartado"
  | "nao_contactar";

// NOVO: classificação automática de qualidade do lead
export type LeadClassificacao =
  | "excelente"
  | "bom"
  | "fraco"
  | "lixo"
  | "pendente";

export type ConfiancaField =
  | "alta"
  | "media"
  | "baixa"
  | "desconhecida";

export type JobStatus =
  | "pendente"
  | "a_correr"
  | "concluido"
  | "erro"
  | "cancelado";

export interface Company {
  id: string;
  job_id?: string;       // NOVO: FK para o job que gerou este lead
  nome: string;
  nicho?: string;
  localidade?: string;
  morada?: string;
  codigo_postal?: string;
  pais?: string;

  // Contacts
  telefone?: string;
  telefone2?: string;
  email?: string;
  website?: string;

  // Social media
  facebook?: string;
  instagram?: string;
  linkedin?: string;
  youtube?: string;
  tiktok?: string;

  // Intelligence flags
  tem_website: boolean;
  tem_loja_online: boolean;
  tem_facebook: boolean;
  tem_instagram: boolean;
  tem_linkedin: boolean;
  tem_youtube?: boolean;
  tem_tiktok?: boolean;
  tem_google_ads: boolean;
  tem_facebook_ads: boolean;
  tem_gtm: boolean;
  tem_ga4: boolean;
  tem_pixel_meta: boolean;

  // Scores
  score_qualidade_lead?: number;          // NOVO: 0-100
  score_maturidade_digital?: number;      // 0-10
  score_oportunidade_comercial?: number;  // 0-10
  score_prioridade_sdr?: number;          // 0-10

  // Qualidade (NOVO)
  classificacao_lead?: LeadClassificacao;
  motivo_descarte?: string;
  confianca_email?: ConfiancaField;
  confianca_telefone?: ConfiancaField;
  fontes_encontradas?: string[];
  ultima_validacao?: string;

  // CRM status
  status: CompanyStatus;
  notas?: string;

  // Metadata
  fonte?: string;
  data_criacao: string;
  data_atualizacao: string;
}

export interface Job {
  id: string;
  nicho: string;
  localidade: string;
  max_resultados: number;
  status: JobStatus;
  progresso: number;
  total_encontrados: number;
  total_validos?: number;      // NOVO
  total_descartados?: number;  // NOVO
  logs_resumidos?: string;     // NOVO
  mensagem_erro?: string;
  data_inicio: string;
  data_fim?: string;
}

export interface SearchParams {
  nicho: string;
  localidade: string;
  max_resultados?: number;
}

export interface LeadsResponse {
  leads: Company[];
  total: number;
  page: number;
  per_page: number;
}

export interface StatsResponse {
  total_leads: number;
  leads_com_website: number;
  leads_com_instagram: number;
  leads_sem_presenca_digital: number;
  leads_excelentes?: number;    // NOVO
  leads_bons?: number;          // NOVO
  jobs_ativos: number;
  media_score_oportunidade: number;
  media_score_qualidade?: number; // NOVO
}
