"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {ChevronLeft, ChevronRight, FileText} from "lucide-react";
import {IncidentStatusBadge} from "@/components/incident-status";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {INCIDENT_STATUSES, normalizePage, type IncidentListItem, type Page} from "@/lib/incidents";

const PAGE_SIZE = 10;

function readableDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "short"}).format(new Date(value));
}

export function MyReports() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<IncidentListItem> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const query = new URLSearchParams({page: String(page), page_size: String(PAGE_SIZE)});
    if (status) query.set("status", status);
    try {
      const result = await api<Page<IncidentListItem> | IncidentListItem[]>(`/api/v1/incidents/mine?${query}`);
      setData(normalizePage(result));
    } catch (reason) {
      setData(null);
      setError(reason instanceof ApiError && reason.status === 401
        ? "Sign in to view your private reports."
        : reason instanceof Error ? reason.message : "Unable to load your reports.");
    } finally {
      setLoading(false);
    }
  }, [page, status]);

  useEffect(() => { void load(); }, [load]);

  return <div className="space-y-6">
    <div className="card flex flex-wrap items-end justify-between gap-4">
      <label className="min-w-56">
        <span className="label">Filter by status</span>
        <select className="field" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
          <option value="">All statuses</option>
          {INCIDENT_STATUSES.map((item) => <option key={item} value={item}>{item.toLowerCase().replaceAll("_", " ")}</option>)}
        </select>
      </label>
      <p className="max-w-xl text-sm leading-6 text-slate-600">Account authentication is required. A reference code by itself never grants access to a report.</p>
    </div>

    {loading && <div className="card" role="status">Loading your private reports…</div>}
    {!loading && error && <div className="card border-red-200" role="alert"><p className="font-bold text-danger">Reports unavailable</p><p className="mt-2 text-sm text-slate-600">{error}</p><div className="mt-5 flex gap-3"><Link className="rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white" href="/login">Sign in</Link><Button type="button" className="bg-slate-700" onClick={() => void load()}>Try again</Button></div></div>}

    {!loading && data && data.items.length === 0 && <div className="card py-12 text-center"><FileText className="mx-auto text-slate-400" size={38}/><h2 className="mt-4 text-xl font-bold">No matching reports</h2><p className="mt-2 text-sm text-slate-600">Create a demo report or choose a different status filter.</p><Link className="mt-6 inline-flex rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white" href="/report">Report a sighting</Link></div>}

    {!loading && data && data.items.length > 0 && <>
      <div className="grid gap-4">
        {data.items.map((incident) => <article className="card" key={incident.id}>
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
            <div>
              <div className="flex flex-wrap items-center gap-3"><h2 className="text-lg font-black text-forest">{incident.reference_code}</h2><IncidentStatusBadge status={incident.status}/><span className="rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-danger">DEMO</span></div>
              <p className="mt-3 text-sm font-semibold text-slate-700">{incident.city}, {incident.district}, {incident.state}</p>
              <p className="mt-1 text-xs text-slate-500">Sighted {readableDate(incident.sighting_at)} · Urgency: {incident.urgency.toLowerCase()}</p>
            </div>
            <Link className="inline-flex min-h-11 items-center justify-center rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest hover:bg-green-50" href={`/reports/${incident.id}`}>View details</Link>
          </div>
        </article>)}
      </div>
      <div className="flex items-center justify-between gap-4">
        <Button type="button" className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50" disabled={data.page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}><ChevronLeft size={17}/>Previous</Button>
        <p className="text-sm text-slate-600">Page {data.page} of {Math.max(1, data.pages)} · {data.total} report{data.total === 1 ? "" : "s"}</p>
        <Button type="button" disabled={data.pages === 0 || data.page >= data.pages} onClick={() => setPage((current) => current + 1)}>Next<ChevronRight size={17}/></Button>
      </div>
    </>}
  </div>;
}
