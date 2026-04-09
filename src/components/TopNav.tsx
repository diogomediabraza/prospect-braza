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
  const [isEmbedded, setIsEmbedded] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Detect if embedded in CRM (parent window !== self)
    const embedded = typeof window !== "undefined" && window.parent !== window;
    setIsEmbedded(embedded);

    // Check for CRM theme URL parameter
    const params = new URLSearchParams(window.location.search);
    const crmTheme = params.get("crm_theme") as "dark" | "light" | null;

    // Determine initial theme
    let initialTheme: "dark" | "light";
    if (crmTheme) {
      initialTheme = crmTheme;
    } else if (embedded) {
      // Default to dark if embedded without explicit theme
      initialTheme = "dark";
    } else {
      const storedTheme = localStorage.getItem("theme") as "dark" | "light" | null;
      initialTheme = storedTheme || "dark";
    }

    setTheme(initialTheme);
    document.documentElement.setAttribute("data-theme", initialTheme);

    // Listen for postMessage from parent CRM window
    const handleMessage = (e: MessageEvent) => {
      if (e.data?.type === "wb-theme-change" && e.data?.theme) {
        const newTheme = e.data.theme as "dark" | "light";
        setTheme(newTheme);
        document.documentElement.setAttribute("data-theme", newTheme);
        // Don't store in localStorage if controlled by parent
        if (!embedded) {
          localStorage.setItem("theme", newTheme);
        }
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
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
                aria-label={item.label}
                aria-current={isActive ? "page" : undefined}
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

        {/* Theme Toggle — hidden when embedded in CRM */}
        {mounted && !isEmbedded && (
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
