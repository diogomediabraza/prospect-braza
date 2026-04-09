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
  Trash2,
  AlertTriangle,
  Instagram,
  Linkedin,
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  Layers,
} from "lucide-react";
import type { Company, CompanyStatus, LeadClassificacao, ConfiancaField } from "@/lib/types";
import { updateLeadStatus, deleteLead, pushLeadToCrm } from "@/lib/api";
import { Database, UserCheck, Youtube, Music2, Facebook, Copy, Check } from "lucide-react";
import { CompanyStatusBadge } from "./StatusBadge";
import { ScoreBar, ScoreCircle } from "./ScoreBars";
import DigitalPresence from "./DigitalPresence";

interface LeadModalProps {
  company: Company;
  onClose: () => void;
  onUpdate?: (updated: Company) => void;
  onDelete?: (id: string) => void;
}

const STATUS_OPTIONS: { value: CompanyStatus; label: string }[] = [
  { value: "novo",           label: "Novo" },
  { value: "abordado",       label: "Abordado" },
  { value: "em_negociacao",  label: "Em Negociação" },
  { value: "fechado",        label: "Fechado" },
  { value: "descartado",     label: "Descartado" },
  { value: "nao_contactar",  label: "Não Contactar" },
];

// ── Helpers visuais ───────────────────────────────────────────────────────────

const CLASSIF_CONFIG: Record<
  LeadClassificacao,
  { label: string; color: string; bg: string; emoji: string }
> = {
  excelente: { label: "Excelente", color: "#009bc5", bg: "rgba(0,155,197,0.12)", emoji: "⭐" },
  bom:       { label: "Bom",       color: "#9e539b", bg: "rgba(158,83,155,0.12)", emoji: "✅" },
  fraco:     { label: "Fraco",     color: "#f3e600", bg: "rgba(243,230,0,0.12)", emoji: "⚠️" },
  lixo:      { label: "Lixo",      color: "#e6391e", bg: "rgba(230,57,30,0.12)",  emoji: "🗑️" },
  pendente:  { label: "Pendente",  color: "#6b7280", bg: "rgba(107,114,128,0.1)", emoji: "⏳" },
};

function ClassificacaoBlock({ value, score, motivo }: {
  value?: LeadClassificacao;
  score?: number;
  motivo?: string;
}) {
  const cfg = CLASSIF_CONFIG[value ?? "pendente"];
  return (
    <div
      className="flex items-center justify-between p-3 rounded-xl"
      style={{ background: cfg.bg }}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">{cfg.emoji}</span>
        <div>
          <div className="text-sm font-medium" style={{ color: cfg.color }}>
            Lead {cfg.label}
          </div>
          {motivo && (
            <div className="text-xs mt-0.5" style={{ color: "var(--tm)" }}>
              {motivo}
            </div>
          )}
        </div>
      </div>
      {score != null && (
        <div className="text-right">
          <div className="text-2xl font-bold font-mono" style={{ color: cfg.color }}>
            {score}
          </div>
          <div className="text-xs" style={{ color: "var(--tm)" }}>/100</div>
        </div>
      )}
    </div>
  );
}

function ConfiancaIcon({ value }: { value?: ConfiancaField }) {
  if (!value || value === "desconhecida") return null;
  if (value === "alta")  return <ShieldCheck  size={13} style={{ color: "#009bc5" }} aria-label="Confiança alta" />;
  if (value === "media") return <ShieldAlert  size={13} style={{ color: "#f3e600" }} aria-label="Confiança média" />;
  return                        <AlertCircle  size={13} style={{ color: "#e6391e" }} aria-label="Confiança baixa" />;
}

// ─────────────────────────────────────────────────────────────────────────────

export default function LeadModal({ company, onClose, onUpdate, onDelete }: LeadModalProps) {
  const [editing,        setEditing]        = useState(false);
  const [status,         setStatus]         = useState<CompanyStatus>(company.status);
  const [notas,          setNotas]          = useState(company.notas ?? "");
  const [saving,         setSaving]         = useState(false);
  const [confirmDelete,  setConfirmDelete]  = useState(false);
  const [deleting,       setDeleting]       = useState(false);
  const [pushingToCrm,   setPushingToCrm]   = useState(false);
  const [crmPushed,       setCrmPushed]       = useState(!!company.crm_lead_id);
  const [copied,          setCopied]          = useState<string | null>(null);

  // Fechar com Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
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

  const handlePushToCrm = async () => {
    setPushingToCrm(true);
    try {
      const result = await pushLeadToCrm(company.id);
      if (result.ok) {
        setCrmPushed(true);
        // Update the parent list with the new crm_lead_id
        onUpdate?.({ ...company, crm_lead_id: result.crm_lead_id, status: "abordado" });
      } else {
        alert(result.msg || "Erro ao inserir no CRM");
      }
    } catch (err) {
      console.error(err);
      alert("Erro ao inserir no CRM");
    } finally {
      setPushingToCrm(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 1500);
  };

  const handleDelete = async () => {
    if (!confirmDelete) { setConfirmDelete(true); return; }
    setDeleting(true);
    try {
      await deleteLead(company.id);
      onDelete?.(company.id);
      onClose();
    } catch (err) {
      console.error(err);
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-backdrop animate-fade-in"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border animate-slide-up"
        style={{
          background:   "var(--card)",
          borderColor:  "var(--border)",
          boxShadow:    "0 24px 64px rgba(0,0,0,0.6)",
        }}
      >
        {/* ── Header ── */}
        <div className="flex items-start justify-between p-6 border-b" style={{ borderColor: "var(--border)" }}>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="font-display text-2xl tracking-wider truncate" style={{ color: "var(--text)" }}>
                {company.nome}
              </h2>
              <CompanyStatusBadge status={company.status} />
            </div>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              {company.nicho && (
                <span className="text-xs" style={{ color: "var(--ts)" }}>{company.nicho}</span>
              )}
              {company.localidade && (
                <span className="flex items-center gap-1 text-xs" style={{ color: "var(--tm)" }}>
                  <MapPin size={11} />
                  {company.localidade}
                </span>
              )}
              {company.claimed_by && (
                <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(158,83,155,0.12)", color: "#9e539b" }}>
                  <UserCheck size={10} />
                  {company.claimed_by}
                </span>
              )}
              {crmPushed && (
                <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(0,155,197,0.12)", color: "#009bc5" }}>
                  <Database size={10} />
                  No CRM
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 ml-4 flex-shrink-0">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: "#e6391e" }}>
                  <AlertTriangle size={12} className="inline mr-1" />
                  Apagar este lead?
                </span>
                <button
                  className="px-3 py-1 rounded-lg text-xs font-medium"
                  style={{ background: "#e6391e", color: "#fff" }}
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? <Loader2 size={12} className="animate-spin inline" /> : "Confirmar"}
                </button>
                <button
                  className="btn-ghost px-2 py-1 text-xs"
                  onClick={() => setConfirmDelete(false)}
                  disabled={deleting}
                >
                  Cancelar
                </button>
              </div>
            ) : (
              <button
                className="btn-ghost p-2 transition-colors"
                onClick={handleDelete}
                title="Apagar lead"
                style={{ color: "var(--tm)" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#e6391e")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--tm)")}
              >
                <Trash2 size={16} />
              </button>
            )}
            <button className="btn-ghost p-2" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-5">

          {/* ── Classificação e Score de Qualidade — NOVO ── */}
          <ClassificacaoBlock
            value={company.classificacao_lead}
            score={company.score_qualidade_lead}
            motivo={company.motivo_descarte}
          />

          {/* ── Scores operacionais ── */}
          <div className="rounded-xl p-4 flex items-center gap-6" style={{ background: "var(--bg3)" }}>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <ScoreCircle value={company.score_prioridade_sdr} size="lg" />
                <div className="text-xs mt-1" style={{ color: "var(--ts)" }}>
                  Prioridade SDR
                </div>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <ScoreBar label="Maturidade Digital" value={company.score_maturidade_digital} />
              <ScoreBar label="Oportunidade" value={company.score_oportunidade_comercial} color="#f3e600" />
              <ScoreBar label="Prioridade SDR" value={company.score_prioridade_sdr} color="var(--orange)" />
            </div>
          </div>

          {/* ── Inserir no CRM ── */}
          {!crmPushed && (
            <button
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium text-sm transition-all"
              style={{ background: "var(--od)", color: "var(--ol)" }}
              onClick={handlePushToCrm}
              disabled={pushingToCrm}
            >
              {pushingToCrm ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
              Inserir contacto no CRM
            </button>
          )}

          {/* ── Contactos — todos os dados visíveis ── */}
          <div>
            <div className="text-xs font-medium uppercase tracking-wider mb-2" style={{ color: "var(--tm)" }}>
              Dados de Contacto
            </div>
            <div className="grid grid-cols-2 gap-2">
              {company.telefone && (
                <div className="flex items-center gap-2.5 p-3 rounded-lg group" style={{ background: "var(--bg3)" }}>
                  <Phone size={14} style={{ color: "var(--orange)" }} />
                  <a href={`tel:${company.telefone}`} className="text-sm flex-1" style={{ color: "var(--text)" }}>{company.telefone}</a>
                  <ConfiancaIcon value={company.confianca_telefone} />
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => copyToClipboard(company.telefone!, "tel")} title="Copiar">
                    {copied === "tel" ? <Check size={12} style={{ color: "#009bc5" }} /> : <Copy size={12} style={{ color: "var(--tm)" }} />}
                  </button>
                </div>
              )}
              {company.telefone2 && (
                <div className="flex items-center gap-2.5 p-3 rounded-lg group" style={{ background: "var(--bg3)" }}>
                  <Phone size={14} style={{ color: "var(--tm)" }} />
                  <span className="text-sm flex-1" style={{ color: "var(--text)" }}>{company.telefone2}</span>
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => copyToClipboard(company.telefone2!, "tel2")} title="Copiar">
                    {copied === "tel2" ? <Check size={12} style={{ color: "#009bc5" }} /> : <Copy size={12} style={{ color: "var(--tm)" }} />}
                  </button>
                </div>
              )}
              {company.email && (
                <div className="flex items-center gap-2.5 p-3 rounded-lg group" style={{ background: "var(--bg3)" }}>
                  <Mail size={14} style={{ color: "var(--orange)" }} />
                  <a href={`mailto:${company.email}`} className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>{company.email}</a>
                  <ConfiancaIcon value={company.confianca_email} />
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => copyToClipboard(company.email!, "email")} title="Copiar">
                    {copied === "email" ? <Check size={12} style={{ color: "#009bc5" }} /> : <Copy size={12} style={{ color: "var(--tm)" }} />}
                  </button>
                </div>
              )}
              {company.website && (
                <a
                  href={company.website.startsWith("http") ? company.website : `https://${company.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2.5 p-3 rounded-lg"
                  style={{ background: "var(--bg3)" }}
                >
                  <Globe size={14} style={{ color: "var(--orange)" }} />
                  <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>{company.website.replace(/^https?:\/\/(www\.)?/, "")}</span>
                  <ExternalLink size={12} style={{ color: "var(--tm)" }} />
                </a>
              )}
            </div>
          </div>

          {/* ── Redes Sociais — todos os canais ── */}
          <div>
            <div className="text-xs font-medium uppercase tracking-wider mb-2" style={{ color: "var(--tm)" }}>
              Redes Sociais
            </div>
            <div className="grid grid-cols-2 gap-2">
              {company.instagram && (
                <a href={company.instagram.startsWith("http") ? company.instagram : `https://instagram.com/${company.instagram.replace(/^@/, "")}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2.5 p-3 rounded-lg" style={{ background: "var(--bg3)" }}>
                  <Instagram size={14} style={{ color: "#e1306c" }} />
                  <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>
                    {company.instagram.replace(/^https?:\/\/(www\.)?instagram\.com\//, "@")}
                  </span>
                  <ExternalLink size={12} style={{ color: "var(--tm)" }} />
                </a>
              )}
              {company.facebook && (
                <a href={company.facebook.startsWith("http") ? company.facebook : `https://facebook.com/${company.facebook}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2.5 p-3 rounded-lg" style={{ background: "var(--bg3)" }}>
                  <Facebook size={14} style={{ color: "#1877f2" }} />
                  <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>Facebook</span>
                  <ExternalLink size={12} style={{ color: "var(--tm)" }} />
                </a>
              )}
              {company.linkedin && (
                <a href={company.linkedin.startsWith("http") ? company.linkedin : `https://linkedin.com/company/${company.linkedin}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2.5 p-3 rounded-lg" style={{ background: "var(--bg3)" }}>
                  <Linkedin size={14} style={{ color: "#0077b5" }} />
                  <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>LinkedIn</span>
                  <ExternalLink size={12} style={{ color: "var(--tm)" }} />
                </a>
              )}
              {company.youtube && (
                <a href={company.youtube} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2.5 p-3 rounded-lg" style={{ background: "var(--bg3)" }}>
                  <Youtube size={14} style={{ color: "#ff0000" }} />
                  <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>YouTube</span>
                  <ExternalLink size={12} style={{ color: "var(--tm)" }} />
                </a>
              )}
              {company.tiktok && (
                <a href={company.tiktok} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2.5 p-3 rounded-lg" style={{ background: "var(--bg3)" }}>
                  <Music2 size={14} style={{ color: "var(--text)" }} />
                  <span className="text-sm truncate flex-1" style={{ color: "var(--text)" }}>TikTok</span>
                  <ExternalLink size={12} style={{ color: "var(--tm)" }} />
                </a>
              )}
              {!company.instagram && !company.facebook && !company.linkedin && !company.youtube && !company.tiktok && (
                <span className="col-span-2 text-xs p-3" style={{ color: "var(--tm)" }}>Nenhuma rede social encontrada</span>
              )}
            </div>
          </div>

          {/* ── Morada ── */}
          {company.morada && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg" style={{ background: "var(--bg3)" }}>
              <MapPin size={14} className="flex-shrink-0 mt-0.5" style={{ color: "var(--tm)" }} />
              <span className="text-sm" style={{ color: "var(--text)" }}>
                {company.morada}
                {company.codigo_postal ? `, ${company.codigo_postal}` : ""}
                {company.pais ? ` — ${company.pais}` : ""}
              </span>
            </div>
          )}

          {/* ── Presença digital ── */}
          <DigitalPresence company={company} />

          {/* ── Fontes encontradas — NOVO ── */}
          {company.fontes_encontradas && company.fontes_encontradas.length > 0 && (
            <div
              className="flex items-start gap-3 p-3 rounded-xl"
              style={{ background: "var(--bg3)" }}
            >
              <Layers size={14} className="flex-shrink-0 mt-0.5" style={{ color: "var(--tm)" }} />
              <div>
                <div className="text-xs font-medium mb-1" style={{ color: "var(--ts)" }}>
                  Fontes de dados
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {company.fontes_encontradas.map((f) => (
                    <span
                      key={f}
                      className="px-2 py-0.5 rounded-full text-xs"
                      style={{ background: "var(--card)", color: "var(--ts)" }}
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Edição CRM ── */}
          <div
            className="rounded-xl p-4 border"
            style={{ background: "var(--bg3)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="label">CRM</span>
              {!editing ? (
                <button className="btn-ghost py-1 px-2 text-xs" onClick={() => setEditing(true)}>
                  <Edit3 size={13} />
                  Editar
                </button>
              ) : (
                <button className="btn-primary py-1 px-3 text-xs" onClick={handleSave} disabled={saving}>
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
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
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
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
                  <span className="text-xs" style={{ color: "var(--tm)" }}>Status:</span>
                  <CompanyStatusBadge status={company.status} />
                </div>
                {company.notas && (
                  <p className="text-sm" style={{ color: "var(--ts)" }}>{company.notas}</p>
                )}
              </div>
            )}
          </div>

          {/* ── Metadata ── */}
          <div
            className="flex items-center justify-between text-xs flex-wrap gap-2"
            style={{ color: "var(--tm)" }}
          >
            <span>Fonte: {company.fonte ?? "—"}</span>
            {company.ultima_validacao && (
              <span>
                Validado: {new Date(company.ultima_validacao).toLocaleDateString("pt-PT")}
              </span>
            )}
            <span>
              Adicionado: {new Date(company.data_criacao).toLocaleDateString("pt-PT")}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
