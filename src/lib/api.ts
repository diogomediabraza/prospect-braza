import type {
  Company,
  Job,
  LeadsResponse,
  StatsResponse,
  SearchParams,
  CompanyStatus,
} from "./types";

const API_BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
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
  nicho?: string;
  localidade?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}): Promise<LeadsResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  });
  return request(`/leads?${qs}`);
}

export async function getLead(id: string): Promise<Company> {
  return request(`/leads/${id}`);
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
