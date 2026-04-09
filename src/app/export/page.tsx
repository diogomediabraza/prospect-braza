"use client";

import { useState } from "react";
import {
  Download,
  Filter,
  FileSpreadsheet,
  CheckCircle2,
  Loader2,
  Info,
} from "lucide-react";
import { exportLeads } from "@/lib/api";
import type { CompanyStatus } from "@/lib/types";

const STATUS_OPTIONS: { value: CompanyStatus | ""; label: string }[] = [
  { value: "", label: "Todos os status" },
  { value: "novo", label: "Novo" },
  { value: "abordado", label: "Abordado" },
  { value: "em_negociacao", label: "Em Negociação" },
  { value: "fechado", label: "Fechado" },
  { value: "descartado", label: "Descartado" },
];

const CSV_FIELDS = [
  "Nome da Empresa",
  "Nicho / Sector",
  "Localidade",
  "Telefone",
  "Email",
  "Website",
  "Facebook",
  "Instagram",
  "LinkedIn",
  "Tem Website",
  "Tem Instagram",
  "Tem Google Ads",
  "Tem Meta Ads",
  "Score Maturidade Digital",
  "Score Oportunidade Comercial",
  "Score Prioridade SDR",
  "Status CRM",
  "Notas",
  "Data de Criação",
];

export default function ExportPage() {
  const [status, setStatus] = useState<CompanyStatus | "">("");
  const [nicho, setNicho] = useState("");
  const [localidade, setLocalidade] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleExport = async () => {
    setLoading(true);
    setSuccess(false);
    setError("");
    try {
      const blob = await exportLeads({
        ...(status && { status }),
        ...(nicho && { nicho }),
        ...(localidade && { localidade }),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `prospect-braza-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao exportar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Header */}
      <div
        className="border-b px-8 py-5"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        <h1
          className="font-display text-2xl tracking-wider"
          style={{ color: "var(--text)" }}
        >
          EXPORTAR LEADS
        </h1>
        <p className="text-sm" style={{ color: "var(--ts)" }}>
          Exporta a tua base de leads filtrada para CSV
        </p>
      </div>

      <div className="px-8 py-8 max-w-2xl space-y-6">
        {/* Filters */}
        <div className="card p-6 space-y-5">
          <div className="flex items-center gap-2">
            <Filter size={16} style={{ color: "var(--orange)" }} />
            <h2 className="font-medium" style={{ color: "var(--text)" }}>
              Filtros de Exportação
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="label mb-1.5 block">Status CRM</label>
              <select
                className="select"
                value={status}
                onChange={(e) => setStatus(e.target.value as CompanyStatus | "")}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label mb-1.5 block">Nicho</label>
                <input
                  className="input"
                  placeholder="Ex: Restaurantes"
                  value={nicho}
                  onChange={(e) => setNicho(e.target.value)}
                />
              </div>
              <div>
                <label className="label mb-1.5 block">Localidade</label>
                <input
                  className="input"
                  placeholder="Ex: Porto"
                  value={localidade}
                  onChange={(e) => setLocalidade(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Info box */}
          <div
            className="flex items-start gap-3 p-3 rounded-lg text-xs"
            style={{
              background: "var(--bg3)",
              color: "var(--ts)",
            }}
          >
            <Info size={13} className="flex-shrink-0 mt-0.5" style={{ color: "var(--tm)" }} />
            <span>
              Sem filtros activos, o CSV incluirá <strong style={{ color: "var(--text)" }}>todos os leads</strong> da base de dados.
              Podes importar o CSV directamente no HubSpot, Pipedrive, ou qualquer CRM.
            </span>
          </div>

          {error && (
            <p className="text-sm" style={{ color: "#e6391e" }}>
              {error}
            </p>
          )}

          <button
            className="btn-primary w-full justify-center py-3"
            onClick={handleExport}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                A gerar CSV...
              </>
            ) : success ? (
              <>
                <CheckCircle2 size={16} />
                Exportado com sucesso!
              </>
            ) : (
              <>
                <Download size={16} />
                Exportar CSV
              </>
            )}
          </button>
        </div>

        {/* Fields preview */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <FileSpreadsheet size={16} style={{ color: "var(--ts)" }} />
            <h2 className="font-medium" style={{ color: "var(--text)" }}>
              Campos Incluídos no CSV
            </h2>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {CSV_FIELDS.map((field) => (
              <div
                key={field}
                className="flex items-center gap-2 text-xs"
                style={{ color: "var(--ts)" }}
              >
                <span
                  className="w-1 h-1 rounded-full flex-shrink-0"
                  style={{ background: "var(--orange)" }}
                />
                {field}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
