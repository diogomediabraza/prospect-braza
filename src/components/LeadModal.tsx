"use client";

import { useEffect, useState } from "react";
import {
  X,
  Phone,
  Mail,
  Globe,
  MapPin,
  ExternalLink,
  Edit3,
  Save,
  Loader2,
} from "lucide-react";
import type { Company, CompanyStatus } from "@/lib/types";
import { updateLeadStatus } from "@/lib/api";
import { CompanyStatusBadge } from "./StatusBadge";
import { ScoreBar, ScoreCircle } from "./ScoreBars";
import DigitalPresence from "./DigitalPresence";

interface LeadModalProps {
  company: Company;
  onClose: () => void;
  onUpdate?: (updated: Company) => void;
}

const STATUS_OPTIONS: { value: CompanyStatus; label: string }[] = [
  { value: "novo", label: "Novo" },
  { value: "abordado", label: "Abordado" },
  { value: "em_negociacao", label: "Em Negociação" },
  { value: "fechado", label: "Fechado" },
  { value: "descartado", label: "Descartado" },
  { value: "nao_contactar", label: "Não Contactar" },
];

export default function LeadModal({ company, onClose, onUpdate }: LeadModalProps) {
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState<CompanyStatus>(company.status);
  const [notas, setNotas] = useState(company.notas ?? "");
  const [saving, setSaving] = useState(false);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateLeadStatus(company.id, status, notas);
      onUpdate?.(updated);
      setEditing(false);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-backdrop animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border animate-slide-up"
        style={{
          background: "var(--card)",
          borderColor: "var(--border)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between p-6 border-b"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h2
                className="font-display text-2xl tracking-wider truncate"
                style={{ color: "var(--text)" }}
              >
                {company.nome}
              </h2>
              <CompanyStatusBadge status={company.status} />
            </div>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              {company.nicho && (
                <span className="text-xs" style={{ color: "var(--ts)" }}>
                  {company.nicho}
                </span>
              )}
              {company.localidade && (
                <span
                  className="flex items-center gap-1 text-xs"
                  style={{ color: "var(--tm)" }}
                >
                  <MapPin size={11} />
                  {company.localidade}
                </span>
              )}
            </div>
          </div>
          <button
            className="btn-ghost p-2 ml-4 flex-shrink-0"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Scores */}
          <div
            className="rounded-xl p-4 flex items-center gap-6"
            style={{ background: "var(--bg3)" }}
          >
            <div className="flex items-center gap-4">
              <div className="text-center">
                <ScoreCircle value={company.score_prioridade_sdr} size="lg" />
                <div className="text-xs mt-1" style={{ color: "var(--ts)" }}>
                  Prioridade SDR
                </div>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <ScoreBar
                label="Maturidade Digital"
                value={company.score_maturidade_digital}
              />
              <ScoreBar
                label="Oportunidade"
                value={company.score_oportunidade_comercial}
                color="#f59e0b"
              />
              <ScoreBar
                label="Prioridade SDR"
                value={company.score_prioridade_sdr}
                color="var(--orange)"
              />
            </div>
          </div>

          {/* Contact info */}
          <div className="grid grid-cols-2 gap-3">
            {company.telefone && (
              <a
                href={`tel:${company.telefone}`}
                className="flex items-center gap-2.5 p-3 rounded-lg transition-colors"
                style={{ background: "var(--bg3)" }}
              >
                <Phone size={15} style={{ color: "var(--orange)" }} />
                <span className="text-sm" style={{ color: "var(--text)" }}>
                  {company.telefone}
                </span>
              </a>
            )}
            {company.email && (
              <a
                href={`mailto:${company.email}`}
                className="flex items-center gap-2.5 p-3 rounded-lg transition-colors"
                style={{ background: "var(--bg3)" }}
              >
                <Mail size={15} style={{ color: "var(--orange)" }} />
                <span className="text-sm truncate" style={{ color: "var(--text)" }}>
                  {company.email}
                </span>
              </a>
            )}
            {company.website && (
              <a
                href={
                  company.website.startsWith("http")
                    ? company.website
                    : `https://${company.website}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2.5 p-3 rounded-lg transition-colors col-span-2"
                style={{ background: "var(--bg3)" }}
              >
                <Globe size={15} style={{ color: "var(--orange)" }} />
                <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>
                  {company.website}
                </span>
                <ExternalLink size={12} style={{ color: "var(--tm)" }} />
              </a>
            )}
          </div>

          {/* Digital presence */}
          <DigitalPresence company={company} />

          {/* Edit status & notes */}
          <div
            className="rounded-xl p-4 border"
            style={{
              background: "var(--bg3)",
              borderColor: "var(--border)",
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="label">CRM</span>
              {!editing ? (
                <button
                  className="btn-ghost py-1 px-2 text-xs"
                  onClick={() => setEditing(true)}
                >
                  <Edit3 size={13} />
                  Editar
                </button>
              ) : (
                <button
                  className="btn-primary py-1 px-3 text-xs"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Save size={13} />
                  )}
                  Guardar
                </button>
              )}
            </div>

            {editing ? (
              <div className="space-y-3">
                <div>
                  <label className="label mb-1 block">Status</label>
                  <select
                    className="select"
                    value={status}
                    onChange={(e) => setStatus(e.target.value as CompanyStatus)}
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label mb-1 block">Notas</label>
                  <textarea
                    className="input resize-none"
                    rows={3}
                    placeholder="Adicionar notas sobre este lead..."
                    value={notas}
                    onChange={(e) => setNotas(e.target.value)}
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: "var(--tm)" }}>
                    Status:
                  </span>
                  <CompanyStatusBadge status={company.status} />
                </div>
                {company.notas && (
                  <p className="text-sm" style={{ color: "var(--ts)" }}>
                    {company.notas}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Metadata */}
          <div
            className="flex items-center justify-between text-xs"
            style={{ color: "var(--tm)" }}
          >
            <span>Fonte: {company.fonte ?? "Páginas Amarelas"}</span>
            <span>
              Adicionado:{" "}
              {new Date(company.data_criacao).toLocaleDateString("pt-PT")}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
