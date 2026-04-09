"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Briefcase,
  Download,
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

export default function TopNav() {
  const pathname = usePathname();

  return (
    <header
      className="sticky top-0 z-30 border-b flex-shrink-0"
      style={{
        background: "var(--bg2)",
        borderColor: "var(--border)",
      }}
    >
      <div className="flex items-center h-14 px-6 gap-8">
        {/* Logo compacto */}
        <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "var(--orange)" }}
          >
            <Target size={16} className="text-white" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span
              className="font-display text-base tracking-wider leading-none"
              style={{ color: "var(--text)" }}
            >
              PROSPECT
            </span>
            <span
              className="font-display text-[10px] tracking-widest leading-none"
              style={{ color: "var(--ol)" }}
            >
              BRAZA
            </span>
          </div>
        </Link>

        {/* Separator */}
        <div
          className="w-px h-6 flex-shrink-0"
          style={{ background: "var(--border)" }}
        />

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 h-full">
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "relative flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-150",
                  isActive
                    ? ""
                    : "hover:bg-[var(--card)]"
                )}
                style={
                  isActive
                    ? {
                        background: "var(--od)",
                        color: "var(--ol)",
                      }
                    : {
                        color: "var(--ts)",
                      }
                }
              >
                <Icon
                  size={15}
                  style={{ color: isActive ? "var(--orange)" : "var(--tm)" }}
                />
                <span>{item.label}</span>
                {/* Active indicator bar at bottom */}
                {isActive && (
                  <span
                    className="absolute bottom-0 left-3 right-3 h-0.5 rounded-t-full"
                    style={{ background: "var(--orange)" }}
                  />
                )}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
