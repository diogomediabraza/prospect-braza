export type CompanyStatus =
  | "novo"
  | "abordado"
  | "em_negociacao"
  | "fechado"
  | "descartado"
  | "nao_contactar";

export type JobStatus =
  | "pendente"
  | "a_correr"
  | "concluido"
  | "erro"
  | "cancelado";

export interface Company {
  id: string;
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

  // Intelligence
  tem_website: boolean;
  tem_loja_online: boolean;
  tem_facebook: boolean;
  tem_instagram: boolean;
  tem_linkedin: boolean;
  tem_google_ads: boolean;
  tem_facebook_ads: boolean;
  tem_gtm: boolean;
  tem_ga4: boolean;
  tem_pixel_meta: boolean;

  // Scores
  score_maturidade_digital?: number;
  score_oportunidade_comercial?: number;
  score_prioridade_sdr?: number;

  // Status
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
  jobs_ativos: number;
  media_score_oportunidade: number;
}
