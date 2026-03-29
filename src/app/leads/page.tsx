"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search,
  Filter,
  Download,
  Loader2,
  Globe,
  Instagram,
  Phone,
  MapPin,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  X,
  ArrowUpDown,
} from "lucide-react";
import { getLeads, exportLeads } from "@/lib/api";
import type { Company, CompanyStatus } from "@/lib/types";
import { CompanyStatusBadge } from "@/components/StatusBadge";
import { ScoreCircle } from "@/components/ScoreBars";
import DigitalPresence from "@/components/DigitalPresence";
import LeadModal from "@/components/LeadModal";

const STATUS_OPTIONS: { value: CompanyStatus | ""; label: string }[] = [
  { value: "", label: "Todos os status" },
  { value: "novo", label: "Novo" },
  { value: "abordado", label: "Abordado" },
  { value: "em_negociacao", label: "Em Negociação" },
  { value: "fechado", label: "Fechado" },
  { value: "descartado", label: "Descartado" },
  { value: "nao_contactar", label: "Não Contactar" },
];

const SORT_OPTIONS = [
  { value: "score_prioridade_sdr", label: "Prioridade SDR" },
  { value: "score_oportunidade_comercial", label: "Oportunidade" },
  { value: "score_maturidade_digital", label: "Maturidade Digital" },
  { value: "data_criacao", label: "Data de Criação" },
  { value: "nome", label: "Nome" },
];

export default function LeadsPage() {
  const [leads, setLeads] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedLead, setSelectedLead] = useState<Company | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CompanyStatus | "">("");
  const [nicho, setNicho] = useState("");
  const [localidade, setLocalidade] = useState("");
  const [sortBy, setSortBy] = useState("score_prioridade_sdr");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showFilters, setShowFilters] = useState(false);
  const [exporting, setExporting] = useState(false);

  const PER_PAGE = 20;
  const totalPages = Math.ceil(total / PER_PAGE);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getLeads({
        page,
        per_page: PER_PAGE,
        ...(status && { status }),
        ...(nicho && { nicho }),
        ...(localidade && { localidade }),
        ...(search && { search }),
        sort_by: sortBy,
        sort_dir: sortDir,
      });
      setLeads(res.leads);
      setTotal(res.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, status, nicho, localidade, search, sortBy, sortDir]);

  useEffect(() => {
    const timer = setTimeout(loadLeads, 300);
    return () => clearTimeout(timer);
  }, [loadLeads]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportLeads({
        ...(status && { status }),
        ...(nicho && { nicho }),
        ...(localidade && { localidade }),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `prospect-braza-leads-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    } finally {
      setExporting(false);
    }
  };

  const handleLeadUpdate = (updated: Company) => {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    if (selectedLead?.id === updated.id) setSelectedLead(updated);
  };

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
    setPage(1);
  };

  const hasFilters = search || status || nicho || localidade;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Header */}
      <div
        className="border-b px-8 py-5"
        style={{
          background: "var(--bg2)",
          borderColor: "var(--border)",
        }}
      >
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1
              className="font-display text-2xl tracking-wider"
              style={{ color: "var(--text)" }}
            >
              BASE DE LEADS
            </h1>
            <p className="text-sm" style={{ color: "var(--ts)" }}>
              {loading ? "A carregar..." : `${total.toLocaleString("pt-PT")} leads encontrados`}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              className="btn-secondary"
              onClick={() => setShowFilters((v) => !v)}
            >
              <SlidersHorizontal size={15} />
              Filtros
              {hasFilters && (
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: "var(--orange)" }}
                />
              )}
            </button>
            <button
              className="btn-secondary"
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <Download size={15} />
              )}
              Exportar CSV
            </button>
          </div>
        </div>

        {/* Search bar */}
        <div className="mt-4 relative max-w-md">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: "var(--tm)" }}
          />
          <input
            className="input pl-9 pr-4"
            placeholder="Pesquisar por nome, localidade, nicho..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          {search && (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2"
              onClick={() => setSearch("")}
            >
              <X size={13} style={{ color: "var(--tm)" }} />
            </button>
          )}
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div
            className="mt-4 p-4 rounded-xl border grid grid-cols-2 md:grid-cols-4 gap-3 animate-slide-up"
            style={{
              background: "var(--bg3)",
              borderColor: "var(--border)",
            }}
          >
            <div>
              <label className="label mb-1 block">Status</label>
              <select
                className="select"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value as CompanyStatus | "");
                  setPage(1);
                }}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label mb-1 block">Nicho</label>
              <input
                className="input"
                placeholder="Ex: Restaurantes"
                value={nicho}
                onChange={(e) => {
                  setNicho(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <label className="label mb-1 block">Localidade</label>
              <input
                className="input"
                placeholder="Ex: Porto"
                value={localidade}
                onChange={(e) => {
                  setLocalidade(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <div>
              <label className="label mb-1 block">Ordenar por</label>
              <select
                className="select"
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setPage(1);
                }}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {hasFilters && (
              <button
                className="btn-ghost text-xs col-span-full justify-start"
                onClick={() => {
                  setSearch("");
                  setStatus("");
                  setNicho("");
                  setLocalidade("");
                  setPage(1);
                }}
              >
                <X size={13} />
                Limpar filtros
              </button>
            )}
          </div>
        )}

        {/* Sort quick buttons */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {SORT_OPTIONS.slice(0, 3).map((opt) => (
            <button
              key={opt.value}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition-all"
              style={
                sortBy === opt.value
                  ? {
                      background: "var(--od)",
                      color: "var(--ol)",
                    }
                  : {
                      background: "var(--card)",
                      color: "var(--ts)",
                    }
              }
              onClick={() => toggleSort(opt.value)}
            >
              <ArrowUpDown size={11} />
              {opt.label}
              {sortBy === opt.value && (
                <span>{sortDir === "desc" ? "↓" : "↑"}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Lead list */}
      <div className="px-8 py-6">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="shimmer h-20 rounded-xl" />
            ))}
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-20">
            <Filter
              size={40}
              className="mx-auto mb-4"
              style={{ color: "var(--tm)" }}
            />
            <p className="text-lg font-medium" style={{ color: "var(--ts)" }}>
              Nenhum lead encontrado
            </p>
            <p className="text-sm mt-1" style={{ color: "var(--tm)" }}>
              Tenta ajustar os filtros ou iniciar uma nova pesquisa
            </p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            {/* Table header */}
            <div
              className="hidden md:grid grid-cols-12 gap-3 px-5 py-3 border-b text-xs uppercase tracking-wider"
              style={{
                borderColor: "var(--border)",
                color: "var(--tm)",
                background: "var(--card2)",
              }}
            >
              <div className="col-span-4">Empresa</div>
              <div className="col-span-2">Contacto</div>
              <div className="col-span-2">Digital</div>
              <div className="col-span-2 text-center">Score SDR</div>
              <div className="col-span-2 text-right">Status</div>
            </div>

            {leads.map((lead) => (
              <div
                key={lead.id}
                className="grid grid-cols-1 md:grid-cols-12 gap-3 px-5 py-4 cursor-pointer transition-all duration-150 border-b"
                style={{ borderColor: "var(--border)" }}
                onClick={() => setSelectedLead(lead)}
              >
                {/* Company name */}
                <div className="col-span-4 min-w-0">
                  <div
                    className="font-medium text-sm truncate"
                    style={{ color: "var(--text)" }}
                  >
                    {lead.nome}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    {lead.nicho && (
                      <span className="text-xs" style={{ color: "var(--ts)" }}>
                        {lead.nicho}
                      </span>
                    )}
                    {lead.localidade && (
                      <span
                        className="flex items-center gap-0.5 text-xs"
                        style={{ color: "var(--tm)" }}
                      >
                        <MapPin size={10} />
                        {lead.localidade}
                      </span>
                    )}
                  </div>
                </div>

                {/* Contact */}
                <div className="col-span-2 flex flex-col justify-center gap-1">
                  {lead.telefone && (
                    <div
                      className="flex items-center gap-1.5 text-xs"
                      style={{ color: "var(--ts)" }}
                    >
                      <Phone size={11} style={{ color: "var(--tm)" }} />
                      {lead.telefone}
                    </div>
                  )}
                  {lead.website && (
                    <div
                      className="flex items-center gap-1.5 text-xs truncate"
                      style={{ color: "var(--ts)" }}
                    >
                      <Globe size={11} style={{ color: "var(--tm)" }} />
                      <span className="truncate">{lead.website}</span>
                    </div>
                  )}
                </div>

                {/* Digital presence icons */}
                <div className="col-span-2 flex items-center">
                  <DigitalPresence company={lead} compact />
                </div>

                {/* Score */}
                <div className="col-span-2 flex items-center justify-center">
                  <ScoreCircle value={lead.score_prioridade_sdr} size="sm" />
                </div>

                {/* Status */}
                <div className="col-span-2 flex items-center justify-end">
                  <CompanyStatusBadge status={lead.status} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
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

              {/* Page numbers */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p =
                  totalPages <= 5
                    ? i + 1
                    : page <= 3
                    ? i + 1
                    : page >= totalPages - 2
                    ? totalPages - 4 + i
                    : page - 2 + i;
                return (
                  <button
                    key={p}
                    className="w-8 h-8 rounded-lg text-sm font-medium transition-all"
                    style={
                      p === page
                        ? { background: "var(--od)", color: "var(--ol)" }
                        : {
                            background: "var(--card)",
                            color: "var(--ts)",
                          }
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

      {/* Lead detail modal */}
      {selectedLead && (
        <LeadModal
          company={selectedLead}
          onClose={() => setSelectedLead(null)}
          onUpdate={handleLeadUpdate}
        />
      )}
    </div>
  );
}
