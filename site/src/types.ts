export type Job = {
  id: string;
  company_id: string;
  company: string;
  sector: string;
  title: string;
  url: string;
  location: string;
  level: "Intern" | "Graduate" | "Early career";
  category: string;
  posted_at: string | null;
  first_seen: string;
  last_seen: string;
  closed: boolean;
  initial?: boolean;
};

export type ManualCompany = { id: string; name: string; sector: string; url: string; reason: string };

export type Data = { jobs: Job[]; manual?: ManualCompany[]; updated_at?: string; baseline_date?: string };

export type Tracking = { saved: Record<string, string>; applied: Record<string, string> };
