"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Briefcase,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  Calendar,
  StopCircle,
  Trash2,
  Users,
  ChevronRight,
} from "lucide-react";
import { getJobs, cancelJob, deleteJob } from "@/lib/api";
import type { Job, JobStatus } from "@/lib/types";
import { JobStatusBadge } from "@/components/StatusBadge";

function JobCard({
  job,
  onCancel,
  onDelete,
}: {
  job: Job;
  onCancel: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const router = useRouter();
  const isRunning = job.status === "a_correr";
  const isDone = job.status === "concluido";
  const isError = job.status === "erro";
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const duration = (() => {
    if (!job.data_fim && !isRunning) return null;
    const start = new Date(job.data_inicio).getTime();
    const end = job.data_fim ? new Date(job.data_fim).getTime() : Date.now();
    const secs = Math.floor((end - start) / 1000);
    if (secs < 60) return `${secs}s`;
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return `${mins}m ${rem}s`;
  })();

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleting(true);
    try {
      await deleteJob(job.id);
      onDelete(job.id);
    } catch (err) {
      console.error(err);
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  const handleCardClick = () => {
    if (isDone && job.total_encontrados > 0) {
      router.push(
        `/leads?nicho=${encodeURIComponent(job.nicho)}&localidade=${encodeURIComponent(job.localidade)}`
      );
    }
  };

  return (
    <div
      className={`card-hover p-5 space-y-4 ${isRunning ? "animate-pulse-orange" : ""} ${
        isDone && job.total_encontrados > 0 ? "cursor-pointer" : ""
      }`}
      style={
        isRunning
          ? { borderColor: "rgba(255,85,0,0.3)" }
          : isDone
          ? { borderColor: "rgba(0,155,197,0.15)" }
          : isError
          ? { borderColor: "rgba(230,57,30,0.15)" }
          : {}
      }
      onClick={handleCardClick}
    >
      {/* Job header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium" style={{ color: "var(--text)" }}>
              {job.nicho}
            </span>
            <span style={{ color: "var(--tm)" }}>·</span>
            <span style={{ color: "var(--ts)" }}>{job.localidade}</span>
          </div>
          <div className="text-xs font-mono mt-0.5" style={{ color: "var(--tm)" }}>
            #{job.id.slice(0, 12)}...
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <JobStatusBadge status={job.status} showDot />
          {isRunning && (
            <button
              className="btn-ghost p-1.5"
              onClick={(e) => { e.stopPropagation(); onCancel(job.id); }}
              title="Cancelar job"
            >
              <StopCircle size={14} style={{ color: "#e6391e" }} />
            </button>
          )}
          {confirmDelete ? (
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <button
                className="px-2 py-1 rounded-lg text-xs font-medium"
                style={{ background: "#e6391e", color: "#fff" }}
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? <Loader2 size={11} className="animate-spin inline" /> : "Apagar"}
              </button>
              <button
                className="btn-ghost px-1.5 py-1 text-xs"
                onClick={(e) => { e.stopPropagation(); setConfirmDelete(false); }}
              >
                ×
              </button>
            </div>
          ) : (
            <button
              className="btn-ghost p-1.5"
              onClick={handleDelete}
              title="Apagar job"
              style={{ color: "var(--tm)" }}
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar (running only) */}
      {isRunning && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs" style={{ color: "var(--ts)" }}>Progresso</span>
            <span className="text-xs font-mono" style={{ color: "var(--ol)" }}>
              {job.progresso}%
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${job.progresso}%` }} />
          </div>
        </div>
      )}

      {/* Error message */}
      {isError && job.mensagem_erro && (
        <div
          className="flex items-start gap-2 p-3 rounded-lg text-xs"
          style={{ background: "rgba(230,57,30,0.08)", color: "#e6391e" }}
        >
          <AlertCircle size={13} className="flex-shrink-0 mt-0.5" />
          {job.mensagem_erro}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-2">
        <div className="text-center p-2.5 rounded-lg" style={{ background: "var(--bg3)" }}>
          <div className="text-lg font-display tracking-wider" style={{ color: "var(--text)" }}>
            {job.total_encontrados}
          </div>
          <div className="text-xs" style={{ color: "var(--tm)" }}>Total</div>
        </div>
        <div className="text-center p-2.5 rounded-lg" style={{ background: "rgba(0,155,197,0.08)" }}>
          <div className="text-lg font-display tracking-wider" style={{ color: "#009bc5" }}>
            {job.total_validos ?? "—"}
          </div>
          <div className="text-xs" style={{ color: "var(--tm)" }}>Válidos</div>
        </div>
        <div className="text-center p-2.5 rounded-lg" style={{ background: "rgba(230,57,30,0.08)" }}>
          <div className="text-lg font-display tracking-wider" style={{ color: "#e6391e" }}>
            {job.total_descartados ?? "—"}
          </div>
          <div className="text-xs" style={{ color: "var(--tm)" }}>Lixo</div>
        </div>
        <div className="text-center p-2.5 rounded-lg" style={{ background: "var(--bg3)" }}>
          <div className="text-lg font-display tracking-wider" style={{ color: "var(--text)" }}>
            {duration ?? "—"}
          </div>
          <div className="text-xs" style={{ color: "var(--tm)" }}>Duração</div>
        </div>
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between text-xs"
        style={{ color: "var(--tm)" }}
      >
        <span className="flex items-center gap-1">
          <Calendar size={10} />
          {new Date(job.data_inicio).toLocaleString("pt-PT", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
        {isDone && job.total_encontrados > 0 && (
          <span className="flex items-center gap-1" style={{ color: "#009bc5" }}>
            <Users size={10} />
            Ver leads
            <ChevronRight size={10} />
          </span>
        )}
        {isDone && job.total_encontrados === 0 && (
          <span className="flex items-center gap-1" style={{ color: "#009bc5" }}>
            <CheckCircle2 size={10} />
            Concluído
          </span>
        )}
      </div>
    </div>
  );
}

type Filter = "all" | JobStatus;

const FILTER_TABS: { value: Filter; label: string; icon: React.ElementType }[] = [
  { value: "all", label: "Todos", icon: Briefcase },
  { value: "a_correr", label: "A Correr", icon: Loader2 },
  { value: "concluido", label: "Concluídos", icon: CheckCircle2 },
  { value: "erro", label: "Com Erro", icon: AlertCircle },
  { value: "pendente", label: "Pendentes", icon: Clock },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadJobs = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await getJobs();
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
    intervalRef.current = setInterval(() => loadJobs(true), 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const handleCancel = async (id: string) => {
    try {
      const updated = await cancelJob(id);
      setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = (id: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== id));
  };

  const filteredJobs = filter === "all" ? jobs : jobs.filter((j) => j.status === filter);

  const counts = {
    all: jobs.length,
    a_correr: jobs.filter((j) => j.status === "a_correr").length,
    concluido: jobs.filter((j) => j.status === "concluido").length,
    erro: jobs.filter((j) => j.status === "erro").length,
    pendente: jobs.filter((j) => j.status === "pendente").length,
    cancelado: jobs.filter((j) => j.status === "cancelado").length,
  };

  const hasRunning = counts.a_correr > 0;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <div
        className="border-b px-8 py-5"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl tracking-wider" style={{ color: "var(--text)" }}>
              JOBS DE PESQUISA
            </h1>
            <p className="text-sm flex items-center gap-2" style={{ color: "var(--ts)" }}>
              {hasRunning && (
                <>
                  <span
                    className="w-1.5 h-1.5 rounded-full animate-pulse"
                    style={{ background: "var(--orange)" }}
                  />
                  <span style={{ color: "var(--ol)" }}>
                    {counts.a_correr} job{counts.a_correr > 1 ? "s" : ""} a correr
                  </span>
                  ·
                </>
              )}
              {jobs.length} jobs no total · auto-refresh activo
            </p>
          </div>
          <button className="btn-secondary" onClick={() => loadJobs()} disabled={loading}>
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
            Actualizar
          </button>
        </div>

        <div className="flex items-center gap-1.5 mt-5 flex-wrap">
          {FILTER_TABS.map(({ value, label, icon: Icon }) => {
            const count = counts[value as keyof typeof counts];
            const isActive = filter === value;
            return (
              <button
                key={value}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all"
                style={
                  isActive
                    ? { background: "var(--od)", color: "var(--ol)" }
                    : { background: "var(--card)", color: "var(--ts)" }
                }
                onClick={() => setFilter(value)}
              >
                <Icon size={13} className={value === "a_correr" && hasRunning ? "animate-spin" : ""} />
                {label}
                {count > 0 && (
                  <span
                    className="px-1.5 py-0.5 rounded-full text-xs"
                    style={{
                      background: isActive ? "rgba(255,85,0,0.2)" : "var(--bg3)",
                      color: isActive ? "var(--ol)" : "var(--tm)",
                    }}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="px-8 py-6">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="shimmer h-48 rounded-xl" />
            ))}
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-20">
            <Briefcase size={40} className="mx-auto mb-4" style={{ color: "var(--tm)" }} />
            <p className="text-lg font-medium" style={{ color: "var(--ts)" }}>
              {filter === "all" ? "Nenhum job ainda" : `Nenhum job com status "${filter}"`}
            </p>
            <p className="text-sm mt-1" style={{ color: "var(--tm)" }}>
              Vai ao Dashboard para iniciar uma nova pesquisa
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredJobs.map((job) => (
              <JobCard key={job.id} job={job} onCancel={handleCancel} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
