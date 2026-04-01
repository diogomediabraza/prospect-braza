"use client";

import { useState, useEffect } from "react";
import {
  Search,
  MapPin,
  Hash,
  Zap,
  Users,
  Globe,
  Instagram,
  TrendingUp,
  Briefcase,
  ArrowRight,
  Loader2,
  ChevronRight,
  Target,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { createJob, getStats, getJobs } from "@/lib/api";
import type { StatsResponse, Job } from "@/lib/types";
import { JobStatusBadge } from "@/components/StatusBadge";

const NICHOS = [
  "Restaurantes",
  "Clínicas Dentárias",
  "Ginásios",
  "Imobiliárias",
  "Salões de Beleza",
  "Advogados",
  "Contabilistas",
  "Hotéis",
  "Construtoras",
  "Farmácias",
  "Veterinários",
  "Auto-reparação",
  "Lojas de Roupa",
  "Pastelarias",
  "Escolas de Condução",
];

const LOCALIDADES = [
  "Porto",
  "Lisboa",
  "Vila Nova de Gaia",
  "Braga",
  "Coimbra",
  "Aveiro",
  "Funchal",
  "Setúbal",
  "Faro",
  "Évora",
  "Leiria",
  "Viseu",
  "Guimarães",
  "Matosinhos",
  "Cascais",
];

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div
      className="stat-card flex items-start gap-4 card-hover"
      style={
        accent
          ? {
              background: "var(--od)",
              borderColor: "rgba(255,85,0,0.2)",
            }
          : {}
      }
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{
          background: accent ? "rgba(255,85,0,0.2)" : "var(--bg3)",
        }}
      >
        <Icon
          size={18}
          style={{ color: accent ? "var(--orange)" : "var(--ts)" }}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div
          className="text-2xl font-display tracking-wider"
          style={{ color: accent ? "var(--ol)" : "var(--text)" }}
        >
          {value}
        </div>
        <div className="text-sm" style={{ color: "var(--ts)" }}>
          {label}
        </div>
        {sub && (
          <div className="text-xs mt-0.5" style={{ color: "var(--tm)" }}>
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [nicho, setNicho] = useState("");
  const [localidade, setLocalidade] = useState("");
  const [maxResultados, setMaxResultados] = useState(50);
  const [loading, setLoading] = useState(false);
  const [jobCreated, setJobCreated] = useState<Job | null>(null);
  const [error, setError] = useState("");

  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStats(), getJobs()])
      .then(([s, j]) => {
        setStats(s);
        setRecentJobs(j.slice(0, 5));
      })
      .catch(console.error)
      .finally(() => setStatsLoading(false));
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nicho.trim() || !localidade.trim()) {
      setError("Preenche o nicho e a localidade.");
      return;
    }
    setError("");
    setLoading(true);
    setJobCreated(null);
    try {
      const job = await createJob({
        nicho: nicho.trim(),
        localidade: localidade.trim(),
        max_resultados: maxResultados,
      });
      setJobCreated(job);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao iniciar pesquisa");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Hero */}
      <div
        className="relative overflow-hidden border-b px-8 py-10"
        style={{
          background:
            "linear-gradient(180deg, rgba(255,85,0,0.06) 0%, transparent 100%)",
          borderColor: "var(--border)",
        }}
      >
        {/* Glow bg */}
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-40 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse at top, rgba(255,85,0,0.12) 0%, transparent 70%)",
          }}
        />

        <div className="relative max-w-4xl">
          <div className="flex items-center gap-2 mb-3">
            <Target size={14} style={{ color: "var(--orange)" }} />
            <span className="text-xs tracking-widest uppercase" style={{ color: "var(--ol)" }}>
              Motor de Prospecção
            </span>
          </div>
          <h1
            className="font-display text-4xl md:text-5xl tracking-wider mb-2"
            style={{ color: "var(--text)" }}
          >
            PROSPECT{" "}
            <span style={{ color: "var(--orange)" }}>BRAZA</span>
          </h1>
          <p className="text-base max-w-lg" style={{ color: "var(--ts)" }}>
            Encontra empresas B2B, analisa a maturidade digital e prioriza os melhores
            leads para o teu SDR — em segundos.
          </p>
        </div>
      </div>

      <div className="px-8 py-8 space-y-8 max-w-6xl">
        {/* Search form */}
        <div
          className="rounded-2xl border p-6"
          style={{
            background: "var(--card)",
            borderColor: "var(--border)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div className="flex items-center gap-2 mb-5">
            <Search size={16} style={{ color: "var(--orange)" }} />
            <h2 className="font-medium" style={{ color: "var(--text)" }}>
              Nova Pesquisa
            </h2>
          </div>

          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Nicho */}
              <div>
                <label className="label mb-1.5 block">
                  <Hash size={11} className="inline mr-1" />
                  Nicho / Sector
                </label>
                <div className="relative">
                  <input
                    className="input"
                    list="nichos-list"
                    placeholder="Ex: Restaurantes, Clínicas..."
                    value={nicho}
                    onChange={(e) => setNicho(e.target.value)}
                  />
                  <datalist id="nichos-list">
                    {NICHOS.map((n) => (
                      <option key={n} value={n} />
                    ))}
                  </datalist>
                </div>
              </div>

              {/* Localidade */}
              <div>
                <label className="label mb-1.5 block">
                  <MapPin size={11} className="inline mr-1" />
                  Localidade
                </label>
                <input
                  className="input"
                  list="localidades-list"
                  placeholder="Ex: Porto, Lisboa..."
                  value={localidade}
                  onChange={(e) => setLocalidade(e.target.value)}
                />
                <datalist id="localidades-list">
                  {LOCALIDADES.map((l) => (
                    <option key={l} value={l} />
                  ))}
                </datalist>
              </div>

              {/* Max resultados */}
              <div>
                <label className="label mb-1.5 block">
                  <BarChart3 size={11} className="inline mr-1" />
                  Máx. Resultados
                </label>
                <select
                  className="select"
                  value={maxResultados}
                  onChange={(e) => setMaxResultados(Number(e.target.value))}
                >
                  <option value={20}>20 empresas</option>
                  <option value={30}>30 empresas</option>
                  <option value={50}>50 empresas (máx.)</option>
                </select>
              </div>
            </div>

            {error && (
              <p className="text-sm" style={{ color: "#f87171" }}>
                {error}
              </p>
            )}

            {/* Success */}
            {jobCreated && (
              <div
                className="flex items-center justify-between p-4 rounded-xl border"
                style={{
                  background: "rgba(16,185,129,0.08)",
                  borderColor: "rgba(16,185,129,0.2)",
                }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-2 h-2 rounded-full animate-pulse"
                    style={{ background: "#10b981" }}
                  />
                  <div>
                    <div className="text-sm font-medium" style={{ color: "#10b981" }}>
                      Pesquisa iniciada!
                    </div>
                    <div className="text-xs" style={{ color: "var(--ts)" }}>
                      Job #{jobCreated.id.slice(0, 8)} a processar...
                    </div>
                  </div>
                </div>
                <Link
                  href={`/jobs`}
                  className="flex items-center gap-1 text-xs"
                  style={{ color: "#10b981" }}
                >
                  Ver Jobs
                  <ArrowRight size={12} />
                </Link>
              </div>
            )}

            <div className="flex items-center justify-between">
              <p className="text-xs" style={{ color: "var(--tm)" }}>
                A pesquisa demora 1–5 minutos dependendo do volume
              </p>
              <button
                type="submit"
                className="btn-primary"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    A iniciar...
                  </>
                ) : (
                  <>
                    <Zap size={15} />
                    Iniciar Pesquisa
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Stats grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium" style={{ color: "var(--text)" }}>
              Visão Geral
            </h2>
            <Link
              href="/leads"
              className="flex items-center gap-1 text-xs"
              style={{ color: "var(--ts)" }}
            >
              Ver todos os leads
              <ChevronRight size={13} />
            </Link>
          </div>

          {statsLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="stat-card shimmer h-24" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard
                icon={Users}
                label="Total de Leads"
                value={stats?.total_leads ?? 0}
                sub="na base de dados"
                accent
              />
              <StatCard
                icon={Globe}
                label="Com Website"
                value={stats?.leads_com_website ?? 0}
                sub="têm presença web"
              />
              <StatCard
                icon={Instagram}
                label="No Instagram"
                value={stats?.leads_com_instagram ?? 0}
                sub="presença social"
              />
              <StatCard
                icon={TrendingUp}
                label="Sem Presença Digital"
                value={stats?.leads_sem_presenca_digital ?? 0}
                sub="oportunidade máxima"
              />
              <StatCard
                icon={Briefcase}
                label="Jobs Ativos"
                value={stats?.jobs_ativos ?? 0}
                sub="pesquisas em curso"
              />
              <StatCard
                icon={Target}
                label="Score Médio"
                value={
                  stats?.media_score_oportunidade != null
                    ? stats.media_score_oportunidade.toFixed(1)
                    : "—"
                }
                sub="oportunidade comercial"
              />
            </div>
          )}
        </div>

        {/* Recent jobs */}
        {recentJobs.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-medium" style={{ color: "var(--text)" }}>
                Pesquisas Recentes
              </h2>
              <Link
                href="/jobs"
                className="flex items-center gap-1 text-xs"
                style={{ color: "var(--ts)" }}
              >
                Ver todos
                <ChevronRight size={13} />
              </Link>
            </div>

            <div className="card overflow-hidden">
              {recentJobs.map((job) => (
                <div key={job.id} className="table-row">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className="font-medium text-sm"
                        style={{ color: "var(--text)" }}
                      >
                        {job.nicho}
                      </span>
                      <span style={{ color: "var(--tm)" }}>·</span>
                      <span className="text-sm" style={{ color: "var(--ts)" }}>
                        {job.localidade}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-xs" style={{ color: "var(--tm)" }}>
                        {new Date(job.data_inicio).toLocaleDateString("pt-PT")}
                      </span>
                      {job.total_encontrados > 0 && (
                        <span className="text-xs" style={{ color: "var(--ts)" }}>
                          {job.total_encontrados} leads
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Progress */}
                  {job.status === "a_correr" && (
                    <div className="w-24">
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${job.progresso}%` }}
                        />
                      </div>
                      <div
                        className="text-xs mt-0.5 text-right"
                        style={{ color: "var(--ts)" }}
                      >
                        {job.progresso}%
                      </div>
                    </div>
                  )}

                  <JobStatusBadge status={job.status} showDot />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/leads"
            className="card-hover p-5 flex items-center gap-4 group cursor-pointer"
          >
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: "var(--od)" }}
            >
              <Users size={20} style={{ color: "var(--orange)" }} />
            </div>
            <div className="flex-1">
              <div className="font-medium" style={{ color: "var(--text)" }}>
                Base de Leads
              </div>
              <div className="text-sm" style={{ color: "var(--ts)" }}>
                Filtra, pesquisa e gere todos os leads
              </div>
            </div>
            <ArrowRight
              size={16}
              style={{ color: "var(--tm)" }}
              className="group-hover:translate-x-1 transition-transform"
            />
          </Link>

          <Link
            href="/export"
            className="card-hover p-5 flex items-center gap-4 group cursor-pointer"
          >
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(59,130,246,0.1)" }}
            >
              <TrendingUp size={20} style={{ color: "#60a5fa" }} />
            </div>
            <div className="flex-1">
              <div className="font-medium" style={{ color: "var(--text)" }}>
                Exportar CSV
              </div>
              <div className="text-sm" style={{ color: "var(--ts)" }}>
                Exporta leads filtrados para Excel / CRM
              </div>
            </div>
            <ArrowRight
              size={16}
              style={{ color: "var(--tm)" }}
              className="group-hover:translate-x-1 transition-transform"
            />
          </Link>
        </div>
      </div>
    </div>
  );
}

