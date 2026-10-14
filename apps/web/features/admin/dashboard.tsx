"use client";

import Link from "next/link";
import {FormEvent, useCallback, useEffect, useMemo, useState} from "react";
import {ChevronLeft, ChevronRight, Filter, RefreshCw} from "lucide-react";
import {IncidentStatusBadge} from "@/components/incident-status";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {
  INCIDENT_STATUSES,
  formatStatus,
  normalizePage,
  type AdminIncidentListItem,
  type Incident,
  type IncidentStatus,
  type Page,
} from "@/lib/incidents";
import {REGIONS, TARGET_STATES, type RegionState} from "@/lib/regions";

type Overview = {
  total_demo_incidents: number;
  pending_incidents: number;
  organization_verification_queue: number;
};

type Filters = {status: string; state: string; district: string; search: string};

const EMPTY_FILTERS: Filters = {status: "", state: "", district: "", search: ""};
const PAGE_SIZE = 20;
const TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  CREATED: ["UNDER_REVIEW", "CANCELLED", "UNABLE_TO_ASSIST"],
  UNDER_REVIEW: ["ASSIGNED", "CANCELLED", "UNABLE_TO_ASSIST"],
  ASSIGNED: ["IN_PROGRESS", "CANCELLED", "UNABLE_TO_ASSIST"],
  IN_PROGRESS: ["RESOLVED", "UNABLE_TO_ASSIST"],
  RESOLVED: ["CLOSED"],
  CLOSED: [],
  CANCELLED: [],
  UNABLE_TO_ASSIST: ["CLOSED"],
};

function readableDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "short"}).format(new Date(value));
}

export function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [draft, setDraft] = useState<Filters>(EMPTY_FILTERS);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [data, setData] = useState<Page<AdminIncidentListItem> | null>(null);
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Overview>("/api/v1/admin/overview").then(setOverview).catch(() => setOverview(null));
  }, [revision]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const query = new URLSearchParams({page: String(page), page_size: String(PAGE_SIZE)});
    for (const [key, value] of Object.entries(filters)) if (value.trim()) query.set(key, value.trim());
    try {
      const result = await api<Page<AdminIncidentListItem> | AdminIncidentListItem[]>(`/api/v1/admin/incidents?${query}`);
      setData(normalizePage(result));
    } catch (reason) {
      setData(null);
      setError(reason instanceof ApiError && (reason.status === 401 || reason.status === 403)
        ? "A coordinator or administrator account is required to view this protected queue."
        : reason instanceof Error ? reason.message : "Unable to load the incident queue.");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    // The revision token intentionally retriggers the same protected query after a status update.
    void revision;
    void load();
  }, [load, revision]);

  const districts = useMemo(() => draft.state ? REGIONS[draft.state as RegionState] : [], [draft.state]);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setFilters(draft);
  }

  function clearFilters() {
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setPage(1);
  }

  return <div className="space-y-8">
    <div className="rounded-2xl bg-danger px-5 py-4 text-sm font-bold text-white">DEMO OPERATIONS ONLY — Status changes do not dispatch a responder or promise assistance.</div>
    <nav className="flex flex-wrap gap-3" aria-label="Admin areas"><Link className="rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest" href="/admin/rescuers">Rescuer applications</Link><Link className="rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest" href="/admin/bookings">Demo bookings</Link><Link className="rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest" href="/admin/locations">LGD imports</Link><Link className="rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest" href="/admin/incidents">Incident queue</Link></nav>

    {overview && <div className="grid gap-4 sm:grid-cols-3">{[
      ["Demo incidents", overview.total_demo_incidents],
      ["Pending review", overview.pending_incidents],
      ["Verification queue", overview.organization_verification_queue],
    ].map(([label, value]) => <div className="card" key={label}><p className="text-sm font-semibold text-slate-500">{label}</p><p className="mt-2 text-4xl font-black text-forest">{value}</p></div>)}</div>}

    <form className="card" onSubmit={applyFilters}>
      <div className="flex items-center gap-3"><Filter className="text-forest"/><h2 className="text-xl font-black">Filter protected incidents</h2></div>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label><span className="label">Status</span><select className="field" value={draft.status} onChange={(event) => setDraft((current) => ({...current, status: event.target.value}))}><option value="">All statuses</option>{INCIDENT_STATUSES.map((item) => <option key={item} value={item}>{formatStatus(item)}</option>)}</select></label>
        <label><span className="label">State</span><select className="field" value={draft.state} onChange={(event) => setDraft((current) => ({...current, state: event.target.value, district: ""}))}><option value="">All states</option>{TARGET_STATES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label><span className="label">District</span><select className="field" value={draft.district} disabled={!draft.state} onChange={(event) => setDraft((current) => ({...current, district: event.target.value}))}><option value="">All districts</option>{districts.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label><span className="label">Reference, city or district</span><input className="field" maxLength={100} value={draft.search} onChange={(event) => setDraft((current) => ({...current, search: event.target.value}))}/></label>
      </div>
      <div className="mt-5 flex flex-wrap gap-3"><Button type="submit">Apply filters</Button><Button type="button" className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50" onClick={clearFilters}>Clear</Button><Button type="button" className="bg-slate-700" onClick={() => setRevision((current) => current + 1)}><RefreshCw size={17}/>Refresh</Button></div>
    </form>

    {loading && <div className="card" role="status">Loading protected incident queue…</div>}
    {!loading && error && <div className="card border-red-200" role="alert"><h2 className="font-black text-danger">Queue unavailable</h2><p className="mt-2 text-sm leading-6 text-slate-700">{error}</p></div>}

    {!loading && data && <section className="card overflow-x-auto">
      <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-xl font-black">Incidents</h2><p className="mt-2 max-w-2xl text-xs leading-5 text-slate-500">This reduced queue deliberately excludes reporter contact details, precise coordinates, address descriptions, and narrative text.</p></div><span className="rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-danger">DEMO DATA</span></div>
      {data.items.length ? <table className="mt-6 w-full min-w-[980px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3 pr-4">Reference</th><th className="pr-4">Region</th><th className="pr-4">Triage</th><th className="pr-4">Status</th><th>Demo workflow</th></tr></thead><tbody>{data.items.map((incident) => <tr className="border-b align-top last:border-0" key={incident.id}><td className="py-5 pr-4"><strong className="text-forest">{incident.reference_code}</strong><p className="mt-1 text-xs font-normal text-slate-500">{readableDate(incident.created_at)}</p></td><td className="py-5 pr-4">{incident.city}<br/><span className="text-xs text-slate-500">{incident.district}, {incident.state}</span></td><td className="py-5 pr-4"><span className="font-bold">{formatStatus(incident.urgency)}</span>{incident.injury_reported && <span className="mt-2 block rounded bg-red-100 px-2 py-1 text-xs font-bold text-danger">Bite/injury reported · advise 112</span>}{incident.immediate_danger && <span className="mt-2 block rounded bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">Immediate danger</span>}</td><td className="py-5 pr-4"><IncidentStatusBadge status={incident.status}/></td><td className="py-5"><StatusControl key={`${incident.id}-${incident.status}`} incident={incident} onUpdated={() => setRevision((current) => current + 1)}/></td></tr>)}</tbody></table> : <p className="mt-6 rounded-xl bg-mist p-8 text-center text-slate-600">No incidents match the current filters.</p>}
      {data.items.length > 0 && <div className="mt-6 flex items-center justify-between gap-4 border-t pt-5"><Button type="button" className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50" disabled={data.page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}><ChevronLeft size={17}/>Previous</Button><p className="text-sm text-slate-600">Page {data.page} of {Math.max(1, data.pages)} · {data.total} incident{data.total === 1 ? "" : "s"}</p><Button type="button" disabled={data.pages === 0 || data.page >= data.pages} onClick={() => setPage((current) => current + 1)}>Next<ChevronRight size={17}/></Button></div>}
    </section>}
  </div>;
}

function StatusControl({incident, onUpdated}: {incident: AdminIncidentListItem; onUpdated: () => void}) {
  const available = TRANSITIONS[incident.status];
  const [target, setTarget] = useState<IncidentStatus | "">(available[0] ?? "");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!available.length) return <span className="text-xs font-semibold text-slate-500">No further transition</span>;

  async function updateStatus() {
    if (!target) return;
    setBusy(true);
    setError("");
    try {
      await api<Incident>(`/api/v1/admin/incidents/${encodeURIComponent(incident.id)}/status`, {method: "PATCH", body: JSON.stringify({status: target, note: note.trim() || undefined})});
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Status update failed.");
    } finally {
      setBusy(false);
    }
  }

  return <div className="min-w-64 space-y-2"><div className="flex gap-2"><select className="min-h-10 flex-1 rounded-lg border border-slate-300 px-3 text-xs font-semibold" value={target} onChange={(event) => setTarget(event.target.value as IncidentStatus)}>{available.map((item) => <option key={item} value={item}>{formatStatus(item)}</option>)}</select><Button type="button" className="min-h-10 px-3 py-2 text-xs" disabled={busy} onClick={() => void updateStatus()}>{busy ? "Saving…" : "Update"}</Button></div><input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs" maxLength={500} placeholder="Optional audit note" value={note} onChange={(event) => setNote(event.target.value)}/>{error && <p className="text-xs font-semibold text-danger" role="alert">{error}</p>}</div>;
}
