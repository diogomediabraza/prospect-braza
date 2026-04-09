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
        {/* Logo com flame gradient */}
        <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient
                id="flameGradient"
                x1="14"
                y1="0"
                x2="14"
                y2="28"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0%" stopColor="#009bc5" />
                <stop offset="25%" stopColor="#9e539b" />
                <stop offset="50%" stopColor="#e6391e" />
                <stop offset="75%" stopColor="#ea5a1c" />
                <stop offset="100%" stopColor="#f3e600" />
              </linearGradient>
            </defs>
            <path
              d="M14 2C14 2 10 8 10 12C10 15.314 11.79 18.127 14.5 19.5C17.21 18.127 19 15.314 19 12C19 8 15 2 14 2Z"
              fill="url(#flameGradient)"
            />
            <path
              d="M14 16C12.343 16 11 17.343 11 19C11 20.657 12.343 22 14 22C15.657 22 17 20.657 17 19C17 17.343 15.657 16 14 16Z"
              fill="url(#flameGradient)"
            />
            <path
              d="M12 22C11.313 22 10.75 22.589 10.75 23.375C10.75 24.161 11.313 24.75 12 24.75H16C16.687 24.75 17.25 24.161 17.25 23.375C17.25 22.589 16.687 22 16 22H12Z"
              fill="url(#flameGradient)"
            />
          </svg>
          <div className="flex flex-col items-start">
            <div className="flex items-baseline gap-0.5">
              <span
                className="text-sm font-light leading-none"
                style={{ color: "var(--text)", fontFamily: "Inter" }}
              >
                we
              </span>
              <span
                className="text-sm font-black leading-none"
                style={{ color: "var(--text)", fontFamily: "Inter" }}
              >
                braza
              </span>
            </div>
            <span
              className="text-[8px] tracking-widest leading-none"
              style={{ color: "var(--ts)" }}
            >
              PROSPECÇÃO
            </span>
          </div>
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
