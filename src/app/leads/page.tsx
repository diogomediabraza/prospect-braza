"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Search,
  Filter,
  Download,
  Loader2,
  Globe,
  Instagram,
  Phone,
  Mail,
  MapPin,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
  ArrowUpDown,
  Star,
  Trash2,
  CheckSquare,
  Square,
} from "lucide-react";
import { getLeads, exportLeads, deleteLead } from "@/lib/api";
import type { Company, CompanyStatus, LeadClassificacao } from "@/lib/types";
import { CompanyStatusBadge } from "@/components/StatusBadge";
import { ScoreCircle } from "@/components/ScoreBars";
import DigitalPresence from "@/components/DigitalPresence";
import LeadModal from "@/components/LeadModal";

// ── Classificação badge ──────────────────────────────────────────────────────

const CLASSIF_CONFIG: Record<
  LeadClassificacao,
  { label: string; color: string; bg: string; dot: string }
> = {
  excelente: { label: "Excelente", color: "#10b981", bg: "rgba(16,185,129,0.12)", dot: "#10b981" },
  bom:       { label: "Bom",       color: "#60a5fa", bg: "rgba(96,165,250,0.12)", dot: "#60a5fa" },
  fraco:     { label: "Fraco",     color: "#f59e0b", bg: "rgba(245,158,11,0.12)", dot: "#f59e0b" },
  lixo:      { label: "Lixo",      color: "#ef4444", bg: "rgba(239,68,68,0.12)",  dot: "#ef4444" },
  pendente:  { label: "Pendente",  color: "#6b7280", bg: "rgba(107,114,128,0.1)", dot: "#6b7280" },
};

function ClassificacaoBadge({ value }: { value?: LeadClassificacao }) {
  const cfg = CLASSIF_CONFIG[value ?? "pendente"];
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: cfg.bg, color: cfg.color }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.dot }} />
      {cfg.label}
    </span>
  );
}

// ── Score de qualidade badge (0-100) ─────────────────────────────────────────

function ScoreQualidade({ value }: { value?: number }) {
  if (value == null) return <span style={{ color: "var(--tm)" }}>—</span>;
  const color =
    value >= 60 ? "#10b981" :
    value >= 35 ? "#60a5fa" :
    value >= 10 ? "#f59e0b" : "#ef4444";
  return (
    <span className="font-mono font-bold text-sm" style={{ color }}>
      {value}
      <span className="text-xs font-normal ml-0.5" style={{ color: "var(--tm)" }}>/100</span>
    </span>
  );
}

// ── Confiança badge ──────────────────────────────────────────────────────────

function ConfiancaBadge({ value, label }: { value?: string; label: string }) {
  if (!value || value === "desconhecida") return null;
  const color =
    value === "alta"  ? "#10b981" :
    value === "media" ? "#f59e0b" : "#ef4444";
  return (
    <span className="text-xs" style={{ color }}>
      {label} {value}
    </span>
  );
}

// ── Opções ────────────────────────────────────────────────────────────────────

const STATUS_OPTIONS: { value: CompanyStatus | ""; label: string }[] = [
  { value: "", label: "Todos os status" },
  { value: "novo", label: "Novo" },
  { value: "abordado", label: "Abordado" },
  { value: "em_negociacao", label: "Em Negociação" },
  { value: "fechado", label: "Fechado" },
  { value: "descartado", label: "Descartado" },
  { value: "nao_contactar", label: "Não Contactar" },
];

const CLASSIF_OPTIONS: { value: LeadClassificacao | ""; label: string }[] = [
  { value: "",          label: "Todas as classificações" },
  { value: "excelente", label: "⭐ Excelente" },
  { value: "bom",       label: "✅ Bom" },
  { value: "fraco",     label: "⚠️ Fraco" },
];

const SORT_OPTIONS = [
  { value: "score_qualidade_lead",        label: "Score Qualidade" },
  { value: "score_prioridade_sdr",        label: "Prioridade SDR" },
  { value: "score_oportunidade_comercial", label: "Oportunidade" },
  { value: "score_maturidade_digital",    label: "Maturidade Digital" },
  { value: "data_criacao",               label: "Data de Criação" },
  { value: "nome",                       label: "Nome" },
];

// ── Componente principal ──────────────────────────────────────────────────────

function LeadsPageInner() {
  const searchParams = useSearchParams();
  const [leads,       setLeads]       = useState<Company[]>([]);
  const [total,       setTotal]       = useState(0);
  const [page,        setPage]        = useState(1);
  const [loading,     setLoading]     = useState(true);
  const [selectedLead, setSelectedLead] = useState<Company | null>(null);

  // Filtros
  const [search,      setSearch]      = useState("");
  const [status,      setStatus]      = useState<CompanyStatus | "">("");
  const [classif,     setClassif]     = useState<LeadClassificacao | "">(""); // NOVO
  const [nicho,       setNicho]       = useState(searchParams.get("nicho") ?? "");
  const [localidade,  setLocalidade]  = useState(searchParams.get("localidade") ?? "");
  const [semEmail,    setSemEmail]    = useState(false);     // NOVO
  const [semTelefone, setSemTelefone] = useState(false);     // NOVO
  const [sortBy,      setSortBy]      = useState("score_qualidade_lead");
  const [sortDir,     setSortDir]     = useState<"asc" | "desc">("desc");
  const [showFilters, setShowFilters] = useState(false);
  const [exporting,   setExporting]   = useState(false);

  // Selecção múltipla para bulk delete
  const [selected,    setSelected]    = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const PER_PAGE   = 20;
  const totalPages = Math.ceil(total / PER_PAGE);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        page,
        per_page: PER_PAGE,
        sort_by:  sortBy,
        sort_dir: sortDir,
      };
      if (status)     params.status     = status;
      if (classif)    params.classificacao = classif;   // NOVO
      if (nicho)      params.nicho      = nicho;
      if (localidade) params.localidade = localidade;
      if (search)     params.search     = search;
      if (semEmail)   params.sem_email  = "1";          // NOVO
      if (semTelefone) params.sem_telefone = "1";       // NOVO

      const res = await getLeads(params as Parameters<typeof getLeads>[0]);
      setLeads(res.leads);
      setTotal(res.total);
      setSelected(new Set()); // limpar selecção ao recarregar
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, status, classif, nicho, localidade, search, sortBy, sortDir, semEmail, semTelefone]);

  useEffect(() => {
    const timer = setTimeout(loadLeads, 300);
    return () => clearTimeout(timer);
  }, [loadLeads]);

  // Export CSV
  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportLeads({
        ...(status     && { status }),
        ...(nicho      && { nicho }),
        ...(localidade && { localidade }),
        ...(classif    && { classificacao: classif }),
      });
      const url = URL.createObjectURL(blob);
      const a   = document.createElement("a");
      a.href     = url;
      a.download = `prospect-braza-leads-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    } finally {
      setExporting(false);
    }
  };

  // Callbacks do modal
  const handleLeadUpdate = (updated: Company) => {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    if (selectedLead?.id === updated.id) setSelectedLead(updated);
  };

  const handleLeadDelete = (id: string) => {
    setLeads((prev) => prev.filter((l) => l.id !== id));
    setTotal((prev) => prev - 1);
    setSelectedLead(null);
    setSelected((prev) => { const s = new Set(prev); s.delete(id); return s; });
  };

  // Ordenação rápida
  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
    setPage(1);
  };

  // Selecção múltipla
  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === leads.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(leads.map((l) => l.id)));
    }
  };

  // Bulk delete
  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Apagar ${selected.size} lead(s) seleccionados? Esta acção é irreversível.`)) return;
    setBulkDeleting(true);
    try {
      await Promise.all([...selected].map((id) => deleteLead(id)));
      setLeads((prev) => prev.filter((l) => !selected.has(l.id)));
      setTotal((prev) => prev - selected.size);
      setSelected(new Set());
    } catch (err) {
      console.error(err);
    } finally {
      setBulkDeleting(false);
    }
  };

  const hasFilters = search || status || classif || nicho || localidade || semEmail || semTelefone;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>

      {/* ── Header ── */}
      <div className="border-b px-8 py-5" style={{ background: "var(--bg2)", borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-display text-2xl tracking-wider" style={{ color: "var(--text)" }}>
              BASE DE LEADS
            </h1>
            <p className="text-sm" style={{ color: "var(--ts)" }}>
              {loading ? "A carregar..." : `${total.toLocaleString("pt-PT")} leads encontrados`}
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Bulk delete */}
            {selected.size > 0 && (
              <button
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all"
                style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
              >
                {bulkDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                Apagar {selected.size} seleccionado{selected.size !== 1 ? "s" : ""}
              </button>
            )}

            <button className="btn-secondary" onClick={() => setShowFilters((v) => !v)}>
              <SlidersHorizontal size={15} />
              Filtros
              {hasFilters && (
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--orange)" }} />
              )}
            </button>

            <button className="btn-secondary" onClick={handleExport} disabled={exporting}>
              {exporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
              Exportar CSV
            </button>
          </div>
        </div>

        {/* Barra de pesquisa */}
        <div className="mt-4 relative max-w-md">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--tm)" }} />
          <input
            className="input pl-9 pr-4"
            placeholder="Pesquisar por nome, localidade, nicho..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
          {search && (
            <button className="absolute right-3 top-1/2 -translate-y-1/2" onClick={() => setSearch("")}>
              <X size={13} style={{ color: "var(--tm)" }} />
            </button>
          )}
        </div>

        {/* Painel de filtros */}
        {showFilters && (
          <div
            className="mt-4 p-4 rounded-xl border grid grid-cols-2 md:grid-cols-4 gap-3 animate-slide-up"
            style={{ background: "var(--bg3)", borderColor: "var(--border)" }}
          >
            {/* Classificação — NOVO filtro mais importante */}
            <div>
              <label className="label mb-1 block">Classificação</label>
              <select
                className="select"
                value={classif}
                onChange={(e) => { setClassif(e.target.value as LeadClassificacao | ""); setPage(1); }}
              >
                {CLASSIF_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label mb-1 block">Status CRM</label>
              <select
                className="select"
                value={status}
                onChange={(e) => { setStatus(e.target.value as CompanyStatus | ""); setPage(1); }}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label mb-1 block">Nicho</label>
              <input
                className="input"
                placeholder="Ex: Restaurantes"
                value={nicho}
                onChange={(e) => { setNicho(e.target.value); setPage(1); }}
              />
            </div>

            <div>
              <label className="label mb-1 block">Localidade</label>
              <input
                className="input"
                placeholder="Ex: Porto"
                value={localidade}
                onChange={(e) => { setLocalidade(e.target.value); setPage(1); }}
              />
            </div>

            {/* Filtros rápidos — NOVO */}
            <div className="col-span-full flex items-center gap-4 flex-wrap pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-sm" style={{ color: "var(--ts)" }}>
                <input
                  type="checkbox"
                  checked={semEmail}
                  onChange={(e) => { setSemEmail(e.target.checked); setPage(1); }}
                  className="rounded"
                />
                Sem e-mail
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-sm" style={{ color: "var(--ts)" }}>
                <input
                  type="checkbox"
                  checked={semTelefone}
                  onChange={(e) => { setSemTelefone(e.target.checked); setPage(1); }}
                  className="rounded"
                />
                Sem telefone
              </label>
            </div>

            {hasFilters && (
              <button
                className="btn-ghost text-xs col-span-full justify-start"
                onClick={() => {
                  setSearch(""); setStatus(""); setClassif(""); setNicho("");
                  setLocalidade(""); setSemEmail(false); setSemTelefone(false); setPage(1);
                }}
              >
                <X size={13} />
                Limpar todos os filtros
              </button>
            )}
          </div>
        )}

        {/* Ordenação rápida */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {SORT_OPTIONS.slice(0, 4).map((opt) => (
            <button
              key={opt.value}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition-all"
              style={
                sortBy === opt.value
                  ? { background: "var(--od)", color: "var(--ol)" }
                  : { background: "var(--card)", color: "var(--ts)" }
              }
              onClick={() => toggleSort(opt.value)}
            >
              <ArrowUpDown size={11} />
              {opt.label}
              {sortBy === opt.value && <span>{sortDir === "desc" ? "↓" : "↑"}</span>}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tabela de leads ── */}
      <div className="px-8 py-6">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="shimmer h-20 rounded-xl" />
            ))}
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-20">
            <Filter size={40} className="mx-auto mb-4" style={{ color: "var(--tm)" }} />
            <p className="text-lg font-medium" style={{ color: "var(--ts)" }}>
              Nenhum lead encontrado
            </p>
            <p className="text-sm mt-1" style={{ color: "var(--tm)" }}>
              Tenta ajustar os filtros ou iniciar uma nova pesquisa
            </p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            {/* Cabeçalho da tabela */}
            <div
              className="hidden md:grid grid-cols-12 gap-3 px-5 py-3 border-b text-xs uppercase tracking-wider"
              style={{ borderColor: "var(--border)", color: "var(--tm)", background: "var(--card2)" }}
            >
              {/* Checkbox select-all */}
              <div className="col-span-1 flex items-center">
                <button onClick={toggleSelectAll} className="btn-ghost p-0">
                  {selected.size === leads.length && leads.length > 0
                    ? <CheckSquare size={14} style={{ color: "var(--orange)" }} />
                    : <Square size={14} />
                  }
                </button>
              </div>
              <div className="col-span-3">Empresa</div>
              <div className="col-span-2">Contacto</div>
              <div className="col-span-2">Classificação</div>
              <div className="col-span-2 text-center">Score</div>
              <div className="col-span-2 text-right">Status</div>
            </div>

            {leads.map((lead) => {
              const isSelected = selected.has(lead.id);
              return (
                <div
                  key={lead.id}
                  className="grid grid-cols-1 md:grid-cols-12 gap-3 px-5 py-4 cursor-pointer transition-all duration-150 border-b"
                  style={{
                    borderColor: "var(--border)",
                    background: isSelected ? "rgba(255,85,0,0.04)" : undefined,
                  }}
                  onClick={() => setSelectedLead(lead)}
                >
                  {/* Checkbox */}
                  <div
                    className="col-span-1 hidden md:flex items-center"
                    onClick={(e) => { e.stopPropagation(); toggleSelect(lead.id); }}
                  >
                    {isSelected
                      ? <CheckSquare size={14} style={{ color: "var(--orange)" }} />
                      : <Square size={14} style={{ color: "var(--tm)" }} />
                    }
                  </div>

                  {/* Nome da empresa */}
                  <div className="col-span-3 min-w-0">
                    <div className="font-medium text-sm truncate" style={{ color: "var(--text)" }}>
                      {lead.nome}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      {lead.nicho && (
                        <span className="text-xs" style={{ color: "var(--ts)" }}>{lead.nicho}</span>
                      )}
                      {lead.localidade && (
                        <span className="flex items-center gap-0.5 text-xs" style={{ color: "var(--tm)" }}>
                          <MapPin size={10} />
                          {lead.localidade}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Contacto */}
                  <div className="col-span-2 flex flex-col justify-center gap-0.5">
                    {lead.telefone && (
                      <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--ts)" }}>
                        <Phone size={10} style={{ color: "var(--orange)" }} />
                        {lead.telefone}
                      </div>
                    )}
                    {lead.email && (
                      <div className="flex items-center gap-1.5 text-xs truncate" style={{ color: "var(--ts)" }}>
                        <Mail size={10} style={{ color: "var(--orange)" }} />
                        <span className="truncate">{lead.email}</span>
                      </div>
                    )}
                    {lead.website && (
                      <div className="flex items-center gap-1.5 text-xs truncate" style={{ color: "var(--ts)" }}>
                        <Globe size={10} style={{ color: "var(--tm)" }} />
                        <span className="truncate">
                          {lead.website.replace(/^https?:\/\/(www\.)?/, "")}
                        </span>
                      </div>
                    )}
                    {lead.instagram && !lead.email && !lead.telefone && (
                      <div className="flex items-center gap-1.5 text-xs truncate" style={{ color: "var(--ts)" }}>
                        <Instagram size={10} style={{ color: "#e1306c" }} />
                        <span className="truncate">
                          {lead.instagram.replace(/^https?:\/\/(www\.)?instagram\.com\//, "@")}
                        </span>
                      </div>
                    )}
                    {!lead.telefone && !lead.email && !lead.website && !lead.instagram && (
                      <span className="text-xs" style={{ color: "var(--tm)" }}>— sem contacto —</span>
                    )}
                  </div>

                  {/* Classificação — NOVO */}
                  <div className="col-span-2 flex flex-col justify-center gap-1">
                    <ClassificacaoBadge value={lead.classificacao_lead} />
                    <ScoreQualidade value={lead.score_qualidade_lead} />
                  </div>

                  {/* Score SDR */}
                  <div className="col-span-2 flex items-center justify-center">
                    <ScoreCircle value={lead.score_prioridade_sdr} size="sm" />
                  </div>

                  {/* Status CRM */}
                  <div className="col-span-2 flex items-center justify-end">
                    <CompanyStatusBadge status={lead.status} />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Paginação */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6">
            <span className="text-sm" style={{ color: "var(--ts)" }}>
              Página {page} de {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                className="btn-secondary px-3 py-2"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft size={15} />
              </button>

              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p =
                  totalPages <= 5 ? i + 1 :
                  page <= 3       ? i + 1 :
                  page >= totalPages - 2 ? totalPages - 4 + i :
                  page - 2 + i;
                return (
                  <button
                    key={p}
                    className="w-8 h-8 rounded-lg text-sm font-medium transition-all"
                    style={
                      p === page
                        ? { background: "var(--od)", color: "var(--ol)" }
                        : { background: "var(--card)", color: "var(--ts)" }
                    }
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </button>
                );
              })}

              <button
                className="btn-secondary px-3 py-2"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal de detalhe */}
      {selectedLead && (
        <LeadModal
          company={selectedLead}
          onClose={() => setSelectedLead(null)}
          onUpdate={handleLeadUpdate}
          onDelete={handleLeadDelete}
        />
      )}
    </div>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ background: "var(--bg)" }} />}>
      <LeadsPageInner />
    </Suspense>
  );
}
