"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Briefcase,
  Download,
  Zap,
  ChevronRight,
  Target,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Leads",
    href: "/leads",
    icon: Users,
  },
  {
    label: "Jobs",
    href: "/jobs",
    icon: Briefcase,
  },
  {
    label: "Exportar",
    href: "/export",
    icon: Download,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex flex-col w-60 min-h-screen flex-shrink-0 border-r"
      style={{
        background: "var(--bg2)",
        borderColor: "var(--border)",
      }}
    >
      {/* Logo */}
      <div className="px-5 py-6 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: "var(--orange)" }}
          >
            <Target size={18} className="text-white" />
          </div>
          <div>
            <div
              className="font-display text-xl leading-none tracking-wider"
              style={{ color: "var(--text)" }}
            >
              PROSPECT
            </div>
            <div
              className="font-display text-xs tracking-widest"
              style={{ color: "var(--ol)" }}
            >
              BRAZA
            </div>
          </div>
        </div>
        <div
          className="mt-3 text-xs"
          style={{ color: "var(--tm)" }}
        >
          Motor de Prospecção B2B
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <div className="label px-2 mb-3">Menu</div>

        {navItems.map((item) => {
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group",
                isActive
                  ? "text-white"
                  : "hover:bg-[var(--card)]"
              )}
              style={
                isActive
                  ? {
                      background: "var(--od)",
                      color: "var(--ol)",
                      borderLeft: "2px solid var(--orange)",
                    }
                  : {
                      color: "var(--ts)",
                    }
              }
            >
              <Icon
                size={16}
                style={{ color: isActive ? "var(--orange)" : "var(--tm)" }}
                className="transition-colors group-hover:text-[var(--ts)]"
              />
              <span className="flex-1">{item.label}</span>
              {isActive && (
                <ChevronRight size={14} style={{ color: "var(--orange)" }} />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <Zap size={12} style={{ color: "var(--orange)" }} />
          <span className="text-xs" style={{ color: "var(--tm)" }}>
            We Braza Group
          </span>
        </div>
        <div className="text-xs mt-0.5" style={{ color: "var(--tm)", fontSize: "10px" }}>
          v1.0.0 · Powered by AI
        </div>
      </div>
    </aside>
  );
}
