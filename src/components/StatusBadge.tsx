import type { CompanyStatus, JobStatus } from "@/lib/types";
import clsx from "clsx";

const COMPANY_STATUS: Record<
  CompanyStatus,
  { label: string; className: string }
> = {
  novo: { label: "Novo", className: "badge-orange" },
  abordado: { label: "Abordado", className: "badge-blue" },
  em_negociacao: { label: "Em Negociação", className: "badge-yellow" },
  fechado: { label: "Fechado", className: "badge-green" },
  descartado: { label: "Descartado", className: "badge-gray" },
  nao_contactar: { label: "Não Contactar", className: "badge-red" },
};

const JOB_STATUS: Record<JobStatus, { label: string; className: string }> = {
  pendente: { label: "Pendente", className: "badge-gray" },
  a_correr: { label: "A Correr", className: "badge-orange" },
  concluido: { label: "Concluído", className: "badge-green" },
  erro: { label: "Erro", className: "badge-red" },
  cancelado: { label: "Cancelado", className: "badge-gray" },
};

interface CompanyStatusBadgeProps {
  status: CompanyStatus;
}

export function CompanyStatusBadge({ status }: CompanyStatusBadgeProps) {
  const config = COMPANY_STATUS[status] ?? {
    label: status,
    className: "badge-gray",
  };
  return <span className={clsx("badge", config.className)}>{config.label}</span>;
}

interface JobStatusBadgeProps {
  status: JobStatus;
  showDot?: boolean;
}

export function JobStatusBadge({ status, showDot }: JobStatusBadgeProps) {
  const config = JOB_STATUS[status] ?? {
    label: status,
    className: "badge-gray",
  };
  return (
    <span className={clsx("badge", config.className)}>
      {showDot && status === "a_correr" && (
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse"
          style={{ background: "var(--orange)" }}
        />
      )}
      {config.label}
    </span>
  );
}
