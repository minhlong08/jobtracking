import { useEffect, useMemo, useState } from "react";
import type { Data, Job, ManualCompany, Tracking } from "./types";
import { useTracking } from "./storage";
import {
  CATEGORIES, CITIES, LEVELS, ago, cityOf, companyColor, daysAgo, initials, isNew, longDate, postedDate,
} from "./util";

type Tab = "all" | "saved" | "applied" | "manual";
type Filters = {
  q: string;
  city: string;
  categories: string[];
  levels: string[];
  within: number;
  company: string;
  hideApplied: boolean;
  showClosed: boolean;
  sort: "newest" | "company";
};

const DEFAULT_FILTERS: Filters = {
  q: "", city: "", categories: [], levels: [], within: 30, company: "", hideApplied: false, showClosed: false, sort: "newest",
};

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("all");
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mobileDetail, setMobileDetail] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { tracking, toggle } = useTracking();

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}jobs.json`, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  const jobs = data?.jobs ?? [];
  const recent = useMemo(() => jobs.filter((j) => daysAgo(j.first_seen) <= 30), [jobs]);
  const newToday = recent.filter((j) => isNew(j) && !j.closed).length;
  const companies = useMemo(() => [...new Set(recent.map((j) => j.company))].sort(), [recent]);

  const visible = useMemo(() => {
    const q = filters.q.trim().toLowerCase();
    let list = recent.filter((j) => {
      if (tab === "saved" && !tracking.saved[j.id]) return false;
      if (tab === "applied" && !tracking.applied[j.id]) return false;
      if (tab === "all") {
        if (!filters.showClosed && j.closed) return false;
        if (filters.hideApplied && tracking.applied[j.id]) return false;
        if (daysAgo(j.first_seen) > filters.within) return false;
      }
      if (q && !`${j.title} ${j.company} ${j.location}`.toLowerCase().includes(q)) return false;
      if (filters.city && !cityOf(j).includes(filters.city)) return false;
      if (filters.categories.length && !filters.categories.includes(j.category)) return false;
      if (filters.levels.length && !filters.levels.includes(j.level)) return false;
      if (filters.company && j.company !== filters.company) return false;
      return true;
    });
    list = [...list].sort((a, b) =>
      filters.sort === "company"
        ? a.company.localeCompare(b.company) || a.title.localeCompare(b.title)
        : Number(isNew(b)) - Number(isNew(a)) || postedDate(b).localeCompare(postedDate(a)),
    );
    return list;
  }, [recent, tab, filters, tracking]);

  const selected = visible.find((j) => j.id === selectedId) ?? visible[0] ?? null;
  const set = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));
  const filtersActive = JSON.stringify({ ...filters, sort: "newest" }) !== JSON.stringify(DEFAULT_FILTERS);

  const open = (id: string) => {
    setSelectedId(id);
    setMobileDetail(true);
    if (window.matchMedia("(max-width: 820px)").matches) window.scrollTo({ top: 0 });
  };

  return (
    <div className={`app ${mobileDetail && tab !== "manual" ? "detail-mode" : ""}`}>
      <header className="masthead">
        <div className="brand">
          <span className="logo" aria-hidden />
          <h1>Intern Tracker</h1>
        </div>
        <p className="today">
          {data ? (
            <>
              <mark>{newToday} new today</mark>
              <span className="muted">
                {recent.filter((j) => !j.closed).length} open roles from the last 30 days
                {data.updated_at && <>, updated {new Date(data.updated_at).toLocaleString("en-AU", { weekday: "short", hour: "numeric", minute: "2-digit" })}</>}
              </span>
            </>
          ) : (
            <span className="muted">{error ? "" : "Loading roles"}</span>
          )}
        </p>
      </header>

      <section className="searchbar" aria-label="Search">
        <label className="field grow">
          <span className="sr-only">Keywords</span>
          <input
            type="search"
            placeholder="Search title, company or location"
            value={filters.q}
            onChange={(e) => set({ q: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="sr-only">City</span>
          <select value={filters.city} onChange={(e) => set({ city: e.target.value })}>
            <option value="">All of Australia</option>
            {CITIES.map((c) => <option key={c}>{c}</option>)}
            <option>Other</option>
          </select>
        </label>
      </section>

      <nav className="tabs" aria-label="Lists">
        {([
          ["all", "All roles", recent.filter((j) => !j.closed).length],
          ["saved", "Saved", Object.keys(tracking.saved).length],
          ["applied", "Applied", Object.keys(tracking.applied).length],
          ["manual", "Check manually", data?.manual?.length ?? 0],
        ] as [Tab, string, number][]).map(([key, label, n]) => (
          <button key={key} className="tab" aria-current={tab === key} onClick={() => { setTab(key); setMobileDetail(false); }}>
            {label} <span className="count">{n}</span>
          </button>
        ))}
      </nav>

      {tab !== "manual" && (
        <button className="btn filters-toggle" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((o) => !o)}>
          {filtersOpen ? "Hide filters" : filtersActive ? "Filters (on)" : "Filters"}
        </button>
      )}
      {tab !== "manual" && (
        <section className={`filters ${filtersOpen ? "open" : ""}`} aria-label="Filters">
          <div className="chips" role="group" aria-label="Role type">
            {CATEGORIES.map((c) => (
              <Chip key={c} on={filters.categories.includes(c)} onClick={() => set({ categories: toggleIn(filters.categories, c) })}>{c}</Chip>
            ))}
          </div>
          <div className="chips" role="group" aria-label="Level">
            {LEVELS.map((l) => (
              <Chip key={l} on={filters.levels.includes(l)} onClick={() => set({ levels: toggleIn(filters.levels, l) })}>{l}</Chip>
            ))}
          </div>
          <div className="filter-row">
            <select value={filters.company} onChange={(e) => set({ company: e.target.value })} aria-label="Company">
              <option value="">Any company</option>
              {companies.map((c) => <option key={c}>{c}</option>)}
            </select>
            {tab === "all" && (
              <select value={filters.within} onChange={(e) => set({ within: Number(e.target.value) })} aria-label="Found within">
                <option value={1}>Found in the last day</option>
                <option value={7}>Found in the last 7 days</option>
                <option value={14}>Found in the last 14 days</option>
                <option value={30}>Found in the last 30 days</option>
              </select>
            )}
            <select value={filters.sort} onChange={(e) => set({ sort: e.target.value as Filters["sort"] })} aria-label="Sort">
              <option value="newest">Newest first</option>
              <option value="company">By company</option>
            </select>
            {tab === "all" && (
              <>
                <label className="check"><input type="checkbox" checked={filters.hideApplied} onChange={(e) => set({ hideApplied: e.target.checked })} /> Hide applied</label>
                <label className="check"><input type="checkbox" checked={filters.showClosed} onChange={(e) => set({ showClosed: e.target.checked })} /> Show closed</label>
              </>
            )}
            {filtersActive && <button className="link" onClick={() => setFilters({ ...DEFAULT_FILTERS, sort: filters.sort })}>Clear filters</button>}
          </div>
        </section>
      )}

      {error ? (
        <Empty title="Couldn't load roles" body={`jobs.json failed to load (${error}). Check that the daily workflow has run and published the site.`} />
      ) : tab === "manual" ? (
        <ManualList items={data?.manual ?? []} />
      ) : (
        <main className={`split ${mobileDetail ? "show-detail" : ""}`}>
          <ol className="list" aria-label="Roles">
            {visible.map((j) => (
              <li key={j.id}>
                <JobCard job={j} tracking={tracking} active={selected?.id === j.id} onOpen={() => open(j.id)} />
              </li>
            ))}
            {data && visible.length === 0 && <Empty title={emptyTitle(tab)} body={emptyBody(tab, filtersActive)} />}
          </ol>
          <div className="detail-wrap">
            {selected && (
              <Detail
                job={selected}
                tracking={tracking}
                onToggle={toggle}
                onBack={() => setMobileDetail(false)}
              />
            )}
          </div>
        </main>
      )}
    </div>
  );
}

function toggleIn(list: string[], v: string) {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function emptyTitle(tab: Tab) {
  return tab === "saved" ? "No saved roles yet" : tab === "applied" ? "Nothing marked as applied" : "No roles match";
}
function emptyBody(tab: Tab, filtersActive: boolean) {
  if (tab === "saved") return "Save a role from its detail panel to keep it here.";
  if (tab === "applied") return "After applying, mark the role as applied to track it here.";
  return filtersActive ? "Clear some filters to see more roles." : "New roles appear here after the next daily check.";
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button className="chip" aria-pressed={on} onClick={onClick}>{children}</button>;
}

function Logo({ name, size = 40 }: { name: string; size?: number }) {
  return (
    <span className="co-logo" style={{ background: companyColor(name), width: size, height: size, fontSize: size * 0.38 }} aria-hidden>
      {initials(name)}
    </span>
  );
}

function JobCard({ job, tracking, active, onOpen }: { job: Job; tracking: Tracking; active: boolean; onOpen: () => void }) {
  const fresh = isNew(job);
  return (
    <button className={`card ${active ? "active" : ""} ${job.closed ? "closed" : ""}`} onClick={onOpen} aria-current={active}>
      <Logo name={job.company} />
      <span className="card-body">
        <span className="card-title">{job.title}</span>
        <span className="card-co">{job.company}</span>
        <span className="card-loc">{job.location}</span>
        <span className="tags">
          {fresh && <span className="tag new">New</span>}
          <span className="tag">{job.level}</span>
          <span className="tag soft">{job.category}</span>
          {tracking.applied[job.id] && <span className="tag done">Applied</span>}
          {!tracking.applied[job.id] && tracking.saved[job.id] && <span className="tag saved">Saved</span>}
          {job.closed && <span className="tag">Closed</span>}
        </span>
      </span>
      <span className="card-when">{ago(postedDate(job))}</span>
    </button>
  );
}

function Detail({ job, tracking, onToggle, onBack }: {
  job: Job; tracking: Tracking; onToggle: (k: keyof Tracking, id: string) => void; onBack: () => void;
}) {
  const [askApplied, setAskApplied] = useState(false);
  useEffect(() => setAskApplied(false), [job.id]);
  const saved = !!tracking.saved[job.id];
  const applied = tracking.applied[job.id];

  return (
    <article className="detail" aria-label={job.title}>
      <button className="back link" onClick={onBack}>Back to roles</button>
      <div className="detail-head">
        <Logo name={job.company} size={56} />
        <div>
          <h2>{job.title}</h2>
          <p className="detail-co">{job.company}</p>
        </div>
      </div>

      <div className="actions">
        <a className="btn primary" href={job.url} target="_blank" rel="noopener noreferrer" onClick={() => !applied && setAskApplied(true)}>
          Apply on company site
        </a>
        <button className="btn" aria-pressed={saved} onClick={() => onToggle("saved", job.id)}>{saved ? "Saved" : "Save"}</button>
        <button className="btn" aria-pressed={!!applied} onClick={() => { onToggle("applied", job.id); setAskApplied(false); }}>
          {applied ? `Applied ${new Date(applied).toLocaleDateString("en-AU", { day: "numeric", month: "short" })}` : "Mark as applied"}
        </button>
      </div>

      {askApplied && !applied && (
        <div className="prompt" role="status">
          <span>Finished your application?</span>
          <button className="btn small primary" onClick={() => { onToggle("applied", job.id); setAskApplied(false); }}>Mark as applied</button>
          <button className="link" onClick={() => setAskApplied(false)}>Not yet</button>
        </div>
      )}

      {job.closed && <p className="notice">This role no longer appears on the company's careers site. It may have closed.</p>}

      <dl className="facts">
        <dt>Location</dt><dd>{job.location}</dd>
        <dt>Level</dt><dd>{job.level}</dd>
        <dt>Role type</dt><dd>{job.category}</dd>
        <dt>Industry</dt><dd>{job.sector}</dd>
        {job.posted_at && <><dt>Posted</dt><dd>{longDate(job.posted_at)}</dd></>}
        <dt>First found</dt><dd>{longDate(job.first_seen)}</dd>
        <dt>Last checked</dt><dd>{longDate(job.last_seen)}</dd>
      </dl>
      <p className="fineprint">Full description and application form are on {new URL(job.url).hostname}.</p>
    </article>
  );
}

function ManualList({ items }: { items: ManualCompany[] }) {
  if (!items.length) return <Empty title="Every company is tracked automatically" body="Nothing needs a manual check." />;
  return (
    <section className="manual">
      <p className="muted">These careers sites block automated checks or have moved, so check them yourself now and then.</p>
      <ul>
        {items.map((m) => (
          <li key={m.id}>
            <Logo name={m.name} size={32} />
            <span className="manual-name"><a href={m.url} target="_blank" rel="noopener noreferrer">{m.name}</a><span className="muted">{m.sector}</span></span>
            <span className="muted manual-why">{m.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      <p className="muted">{body}</p>
    </div>
  );
}
