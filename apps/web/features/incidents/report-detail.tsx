"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {CalendarClock, ExternalLink, ImageIcon, MapPin, ShieldCheck, TriangleAlert} from "lucide-react";
import {IncidentStatusBadge} from "@/components/incident-status";
import {Button} from "@/components/ui/button";
import {api, ApiError, mediaUrl} from "@/lib/api";
import {canCitizenCancel, formatStatus, type Incident, type IncidentEvent} from "@/lib/incidents";

function readableDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "short"}).format(new Date(value));
}

export function ReportDetail({incidentId}: {incidentId: string}) {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextIncident, nextEvents] = await Promise.all([
        api<Incident>(`/api/v1/incidents/${encodeURIComponent(incidentId)}`),
        api<IncidentEvent[]>(`/api/v1/incidents/${encodeURIComponent(incidentId)}/events`),
      ]);
      setIncident(nextIncident);
      setEvents(nextEvents);
    } catch (reason) {
      setIncident(null);
      setEvents([]);
      setError(reason instanceof ApiError && reason.status === 401
        ? "Sign in with the account that created this report."
        : reason instanceof ApiError && reason.status === 403
          ? "This report belongs to another account and cannot be viewed."
          : reason instanceof Error ? reason.message : "Unable to load this report.");
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => { void load(); }, [load]);

  async function cancelReport() {
    if (!incident || !window.confirm("Cancel this demo report? This action cannot be undone.")) return;
    setCancelling(true);
    setError("");
    try {
      const cancelled = await api<Incident>(`/api/v1/incidents/${encodeURIComponent(incident.id)}/cancel`, {method: "POST"});
      const nextEvents = await api<IncidentEvent[]>(`/api/v1/incidents/${encodeURIComponent(incident.id)}/events`);
      setIncident(cancelled);
      setEvents(nextEvents);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The report could not be cancelled.");
    } finally {
      setCancelling(false);
    }
  }

  if (loading) return <div className="card" role="status">Loading your private report…</div>;
  if (!incident) return <div className="card border-red-200" role="alert"><h1 className="text-xl font-black text-danger">Report unavailable</h1><p className="mt-3 text-sm leading-6 text-slate-700">{error}</p><div className="mt-6 flex flex-wrap gap-3"><Link className="rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white" href="/login">Sign in</Link><Link className="rounded-xl border border-forest px-5 py-3 text-sm font-bold text-forest" href="/my-reports">My reports</Link></div></div>;

  const hasCoordinates = incident.latitude !== null && incident.latitude !== undefined && incident.longitude !== null && incident.longitude !== undefined;

  return <div className="space-y-6">
    <div className="rounded-2xl bg-danger px-5 py-4 text-sm font-bold text-white">DEMO RECORD — No responder has been notified or dispatched. For a medical emergency, call <a className="underline" href="tel:112">112</a>.</div>
    <header className="card">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div><p className="eyebrow">Private report</p><h1 className="mt-2 text-3xl font-black">{incident.reference_code}</h1><div className="mt-4 flex flex-wrap gap-2"><IncidentStatusBadge status={incident.status}/><span className="rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-danger">DEMO ONLY</span><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{incident.urgency.toLowerCase()} urgency</span></div></div>
        <div className="flex flex-wrap gap-3"><Link className="rounded-xl border border-forest px-4 py-3 text-sm font-bold text-forest" href="/my-reports">All my reports</Link>{canCitizenCancel(incident.status) && <Button type="button" className="bg-danger hover:bg-red-700" disabled={cancelling} onClick={() => void cancelReport()}>{cancelling ? "Cancelling…" : "Cancel report"}</Button>}</div>
      </div>
      {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-danger" role="alert">{error}</p>}
    </header>

    <div className="grid gap-6 lg:grid-cols-[1.25fr_.75fr]">
      <div className="space-y-6">
        <section className="card"><h2 className="text-xl font-black">Incident details</h2><dl className="mt-5 grid gap-5 sm:grid-cols-2">
          <Detail label="Sighting time" value={readableDate(incident.sighting_at)}/>
          <Detail label="Location" value={`${incident.city}, ${incident.district}, ${incident.state}`}/>
          <Detail label="Landmark" value={incident.landmark || "Not provided"}/>
          <Detail label="Address description" value={incident.address_description || "Not provided"}/>
          <Detail label="Snake visible" value={incident.snake_visible ? "Yes" : "No"}/>
          <Detail label="Immediate danger" value={incident.immediate_danger ? "Yes" : "No"}/>
          <Detail label="Bite or injury reported" value={incident.injury_reported ? "Yes — call 112 and seek medical care" : "No"}/>
        </dl><div className="mt-6 border-t pt-5"><h3 className="text-sm font-bold text-slate-500">Observation</h3><p className="mt-2 whitespace-pre-wrap leading-7 text-slate-700">{incident.description}</p></div></section>

        <section className="card"><div className="flex items-center gap-3"><MapPin className="text-forest"/><h2 className="text-xl font-black">Private location</h2></div><p className="mt-3 text-sm leading-6 text-slate-600">Exact coordinates are visible only to the report owner and authorized coordinators or administrators.</p>{hasCoordinates ? <dl className="mt-5 grid gap-4 sm:grid-cols-3"><Detail label="Latitude" value={Number(incident.latitude).toFixed(6)}/><Detail label="Longitude" value={Number(incident.longitude).toFixed(6)}/><Detail label="GPS accuracy" value={incident.location_accuracy === null || incident.location_accuracy === undefined ? "Not provided" : `±${Math.round(incident.location_accuracy)} m`}/></dl> : <p className="mt-5 rounded-xl bg-mist p-4 text-sm font-semibold text-slate-700">Manual locality was provided; no GPS coordinates were stored.</p>}</section>

        <section className="card"><div className="flex items-center gap-3"><ImageIcon className="text-forest"/><h2 className="text-xl font-black">Private images</h2></div>{incident.media?.length ? <ul className="mt-5 grid gap-3 sm:grid-cols-2">{incident.media.map((item) => <li className="rounded-xl border border-slate-200 p-4" key={item.id}><p className="truncate text-sm font-bold">{item.original_filename}</p><p className="mt-1 text-xs text-slate-500">{Math.max(1, Math.round(item.file_size / 1024))} KB · {item.content_type}</p><a className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-forest" href={mediaUrl(item.download_url)} target="_blank" rel="noreferrer">Open securely <ExternalLink size={15}/></a></li>)}</ul> : <p className="mt-4 text-sm text-slate-600">No optional images were uploaded.</p>}<p className="mt-4 text-xs leading-5 text-slate-500">Media is account-protected and served with private, no-store caching.</p></section>
      </div>

      <aside className="space-y-6">
        {incident.injury_reported && <div className="rounded-2xl bg-danger p-6 text-white"><TriangleAlert/><h2 className="mt-4 text-xl font-black">Medical help first</h2><p className="mt-3 text-sm leading-6 text-red-50">Call 112 and seek immediate medical care. Do not wait for an update to this report.</p><a className="mt-5 inline-flex rounded-xl bg-white px-5 py-3 font-black text-danger" href="tel:112">Call 112</a></div>}
        <section className="card"><div className="flex items-center gap-3"><CalendarClock className="text-forest"/><h2 className="text-xl font-black">Timeline</h2></div>{events.length ? <ol className="mt-6 border-l-2 border-green-100 pl-5">{events.map((event) => <li className="relative pb-7 last:pb-0" key={event.id}><span className="absolute -left-[1.63rem] top-1 h-3 w-3 rounded-full bg-forest ring-4 ring-white"/><p className="text-sm font-black text-forest">{formatStatus(event.event_type)}</p><p className="mt-1 text-xs text-slate-500">{readableDate(event.created_at)}</p>{event.details && <p className="mt-2 text-sm leading-6 text-slate-700">{event.details}</p>}</li>)}</ol> : <p className="mt-4 text-sm text-slate-600">No timeline events are available.</p>}</section>
        <div className="card bg-green-50"><ShieldCheck className="text-forest"/><h2 className="mt-4 font-black">Privacy boundary</h2><p className="mt-2 text-sm leading-6 text-slate-700">This page requires an authenticated owner account. Contact details are not returned in the report response.</p></div>
      </aside>
    </div>
  </div>;
}

function Detail({label, value}: {label: string; value: string}) {
  return <div><dt className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</dt><dd className="mt-1 text-sm font-semibold leading-6 text-slate-800">{value}</dd></div>;
}
