"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Users,
  Briefcase,
  Download,
  Sun,
  Moon,
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
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const storedTheme = localStorage.getItem("theme") as "dark" | "light" | null;
    const initialTheme = storedTheme || "dark";
    setTheme(initialTheme);
    document.documentElement.setAttribute("data-theme", initialTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    document.documentElement.setAttribute("data-theme", newTheme);
  };

  return (
    <header
      className="sticky top-0 z-30 border-b flex-shrink-0"
      style={{
        background: "var(--bg2)",
        borderColor: "var(--border)",
      }}
    >
      <div className="flex items-center h-14 px-6 gap-8 justify-between">
        {/* Logo original WeBraza */}
        <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
          <img
            src={theme === "dark" ? "/branco_horizontal.png" : "/colorido_horizontal.png"}
            alt="WeBraza"
            style={{ height: "30px", width: "auto" }}
          />
          <span
            className="text-[8px] tracking-widest leading-none"
            style={{ color: "var(--ts)" }}
          >
            PROSPECÇÃO
          </span>
        </Link>

        {/* Separator */}
        <div
          className="w-px h-6 flex-shrink-0"
          style={{ background: "var(--border)" }}
        />

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 h-full flex-1">
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

        {/* Theme Toggle */}
        {mounted && (
          <button
            onClick={toggleTheme}
            className="btn-ghost"
            aria-label="Toggle theme"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? (
              <Sun size={18} />
            ) : (
              <Moon size={18} />
            )}
          </button>
        )}
      </div>
    </header>
  );
}
