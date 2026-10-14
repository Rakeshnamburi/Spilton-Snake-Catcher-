"use client";

import Link from "next/link";
import {useState} from "react";
import {IncidentStatusBadge} from "@/components/incident-status";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {normalizePage, type IncidentListItem, type Page} from "@/lib/incidents";

const PAGE_SIZE = 100;

export function TrackForm() {
  const [reference, setReference] = useState("");
  const [result, setResult] = useState<IncidentListItem | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function lookup() {
    const requested = reference.trim().toUpperCase();
    setMessage("");
    setResult(null);
    if (!requested) { setMessage("Enter the report reference shown after submission."); return; }
    setLoading(true);
    try {
      let pageNumber = 1;
      let pageCount = 1;
      do {
        const response = await api<Page<IncidentListItem> | IncidentListItem[]>(`/api/v1/incidents/mine?page=${pageNumber}&page_size=${PAGE_SIZE}`);
        const page = normalizePage(response);
        const found = page.items.find((incident) => incident.reference_code.toUpperCase() === requested);
        if (found) { setResult(found); return; }
        pageCount = page.pages;
        pageNumber += 1;
      } while (pageNumber <= pageCount);
      setMessage("No report with that reference is connected to your signed-in account.");
    } catch (reason) {
      setMessage(reason instanceof ApiError && reason.status === 401
        ? "Sign in before tracking a private report."
        : reason instanceof Error ? reason.message : "Unable to track the report.");
    } finally {
      setLoading(false);
    }
  }

  return <div className="card max-w-2xl">
    <label><span className="label">Report reference</span><div className="mt-2 flex flex-col gap-3 sm:flex-row"><input className="field mt-0 uppercase" placeholder="SPR-…" value={reference} onChange={(event) => setReference(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void lookup(); } }}/><Button onClick={() => void lookup()} disabled={loading} type="button">{loading ? "Checking…" : "Check status"}</Button></div></label>
    <p className="mt-3 text-xs leading-5 text-slate-500">A reference code alone is never enough. The API verifies that you are authenticated as the report owner before returning any information.</p>
    {message && <p role="alert" className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">{message}</p>}
    {result && <div className="mt-6 rounded-2xl border border-green-200 bg-green-50 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><strong>{result.reference_code}</strong><IncidentStatusBadge status={result.status}/></div><p className="mt-3 text-sm text-slate-700">{result.city}, {result.district}, {result.state}</p><p className="mt-2 text-xs font-bold uppercase tracking-widest text-danger">Demo only · no dispatch</p><Link className="mt-5 inline-flex rounded-xl bg-forest px-4 py-3 text-sm font-bold text-white" href={`/reports/${result.id}`}>View private details and timeline</Link></div>}
    <Link className="mt-6 inline-block text-sm font-bold text-forest" href="/my-reports">Browse all my reports</Link>
  </div>;
}
