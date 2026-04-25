import type { Company } from "@/lib/types";
import { Globe, ShoppingBag, Facebook, Instagram, Linkedin, Youtube, Tag, BarChart, Target } from "lucide-react";

interface DigitalPresenceProps {
  company: Company;
  compact?: boolean;
}

const PRESENCE_ICONS = [
  { key: "tem_website", icon: Globe, label: "Website" },
  { key: "tem_loja_online", icon: ShoppingBag, label: "Loja" },
  { key: "tem_facebook", icon: Facebook, label: "Facebook" },
  { key: "tem_instagram", icon: Instagram, label: "Instagram" },
  { key: "tem_linkedin", icon: Linkedin, label: "LinkedIn" },
  { key: "tem_youtube", icon: Youtube, label: "YouTube" },
] as const;

const PIXEL_ICONS = [
  { key: "tem_google_ads", icon: Target, label: "Google Ads" },
  { key: "tem_facebook_ads", icon: Tag, label: "Meta Ads" },
  { key: "tem_gtm", icon: BarChart, label: "GTM" },
  { key: "tem_ga4", icon: BarChart, label: "GA4" },
  { key: "tem_pixel_meta", icon: Tag, label: "Pixel Meta" },
] as const;

export default function DigitalPresence({ company, compact }: DigitalPresenceProps) {
  if (compact) {
    const active = PRESENCE_ICONS.filter((p) => company[p.key as keyof Company]);
    const count = active.length;
    const total = PRESENCE_ICONS.length;
    const pct = (count / total) * 100;
    const color = pct >= 66 ? "#009bc5" : pct >= 33 ? "#f3e600" : "#e6391e";

    return (
      <div className="flex items-center gap-1.5">
        {PRESENCE_ICONS.map(({ key, icon: Icon }) => {
          const active = company[key as keyof Company] as boolean;
          return (
            <Icon
              key={key}
              size={13}
              style={{
                color: active ? color : "var(--tm)",
                opacity: active ? 1 : 0.4,
              }}
            />
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <div className="label mb-2">Presença Digital</div>
        <div className="flex flex-wrap gap-2">
          {PRESENCE_ICONS.map(({ key, icon: Icon, label }) => {
            const isActive = company[key as keyof Company] as boolean;
            return (
              <div
                key={key}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs"
                style={{
                  background: isActive ? "var(--od)" : "var(--bg3)",
                  color: isActive ? "var(--ol)" : "var(--tm)",
                  border: `1px solid ${isActive ? "rgba(255,85,0,0.2)" : "var(--border)"}`,
                }}
              >
                <Icon size={12} />
                {label}
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="label mb-2">Tracking & Ads</div>
        <div className="flex flex-wrap gap-2">
          {PIXEL_ICONS.map(({ key, icon: Icon, label }) => {
            const isActive = company[key as keyof Company] as boolean;
            return (
              <div
                key={key}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs"
                style={{
                  background: isActive ? "rgba(158,83,155,0.1)" : "var(--bg3)",
                  color: isActive ? "#9e539b" : "var(--tm)",
                  border: `1px solid ${isActive ? "rgba(158,83,155,0.2)" : "var(--border)"}`,
                }}
              >
                <Icon size={12} />
                {label}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
