import type {
  Company,
  Job,
  LeadsResponse,
  StatsResponse,
  SearchParams,
  CompanyStatus,
  LeadClassificacao,
} from "./types";

const API_BASE = "/api";

/** Strip Python str(None) → null for all string fields */
function sanitizeCompany(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    result[k] = v === "None" ? null : v;
  }
  return result;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ─── Leads ────────────────────────────────────────────────────────────────────

export async function getLeads(params: {
  page?: number;
  per_page?: number;
  status?: CompanyStatus;
  classificacao?: LeadClassificacao;  // NOVO
  nicho?: string;
  localidade?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  sem_email?: string;                 // NOVO: "1" para filtrar leads sem email
  sem_telefone?: string;              // NOVO: "1" para filtrar leads sem telefone
}): Promise<LeadsResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  });
  const res = await request<LeadsResponse>(`/leads?${qs}`);
  // Sanitize "None" strings from backend Python str(None) bug
  if (res.leads) {
    res.leads = res.leads.map((l) => sanitizeCompany(l as unknown as Record<string, unknown>) as unknown as Company);
  }
  return res;
}

export async function getLead(id: string): Promise<Company> {
  const lead = await request<Company>(`/leads/${id}`);
  return sanitizeCompany(lead as unknown as Record<string, unknown>) as unknown as Company;
}

export async function updateLeadStatus(
  id: string,
  status: CompanyStatus,
  notas?: string
): Promise<Company> {
  return request(`/leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status, notas }),
  });
}

export async function deleteLead(id: string): Promise<void> {
  return request(`/leads/${id}`, { method: "DELETE" });
}

export async function exportLeads(params: {
  status?: CompanyStatus;
  classificacao?: LeadClassificacao;  // NOVO
  nicho?: string;
  localidade?: string;
}): Promise<Blob> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  });
  const res = await fetch(`${API_BASE}/leads/export?${qs}`);
  if (!res.ok) throw new Error("Erro ao exportar");
  return res.blob();
}

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export async function getJobs(): Promise<Job[]> {
  return request("/jobs");
}

export async function getJob(id: string): Promise<Job> {
  return request(`/jobs/${id}`);
}

export async function createJob(params: SearchParams): Promise<Job> {
  return request("/jobs", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function cancelJob(id: string): Promise<Job> {
  return request(`/jobs/${id}/cancel`, { method: "POST" });
}

export async function deleteJob(id: string): Promise<void> {
  return request(`/jobs/${id}`, { method: "DELETE" });
}

// ─── Stats ────────────────────────────────────────────────────────────────────

export async function getStats(): Promise<StatsResponse> {
  return request("/stats");
}
