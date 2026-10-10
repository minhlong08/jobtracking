import type { Job } from "./types";

const DAY = 86_400_000;

export const CITIES = ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Canberra", "Hobart", "Darwin"];
export const CATEGORIES = ["Software", "Data & Analytics", "ML/AI", "Infra/Cloud/Security", "Other tech", "General program"];
export const LEVELS = ["Intern", "Graduate", "Early career"] as const;

export function daysAgo(iso: string, now = new Date()): number {
  const d = new Date(iso + "T00:00:00");
  return Math.max(0, Math.floor((now.getTime() - d.getTime()) / DAY));
}

export function ago(iso: string): string {
  const n = daysAgo(iso);
  if (n === 0) return "Today";
  if (n === 1) return "Yesterday";
  if (n < 30) return `${n}d ago`;
  return new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short" });
}

export function longDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
}

/** A role is "new" when the tracker first found it in the last day, excluding the initial import. */
export const isNew = (j: Job) => !j.initial && daysAgo(j.first_seen) <= 1;

export const postedDate = (j: Job) => j.posted_at ?? j.first_seen;

export function cityOf(j: Job): string[] {
  const loc = j.location.toLowerCase();
  const hits = CITIES.filter((c) => loc.includes(c.toLowerCase()));
  if (/\bact\b|australian capital/.test(loc) && !hits.includes("Canberra")) hits.push("Canberra");
  return hits.length ? hits : ["Other"];
}

const PALETTE = ["#2457D6", "#0E7C66", "#7A4FD1", "#B4462B", "#1F7FA8", "#6B7A1F", "#A23C7A", "#3D5A80"];
export function companyColor(name: string): string {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

export function initials(name: string): string {
  const words = name.replace(/\(.*?\)/g, "").split(/[\s/&.-]+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : name.slice(0, 2)).toUpperCase();
}
