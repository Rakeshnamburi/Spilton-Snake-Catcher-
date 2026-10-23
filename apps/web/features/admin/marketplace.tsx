"use client";

import {FormEvent, useCallback, useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {api, ApiError, API_URL} from "@/lib/api";
import {formatDate, humanize} from "@/lib/marketplace";

type AdminRescuer = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  public_display_name: string | null;
  organization_id: string | null;
  organization: string | null;
  organization_status: string | null;
  verification_status: string;
  authorization_reference: string | null;
  issuing_authority: string | null;
  authorization_expiry: string | null;
  years_experience: number;
  languages: string[];
  availability: string;
  document_count: number;
  created_at: string;
};
type AdminPage<T> = {items: T[]; total: number; page: number; limit: number; pages: number};

export function AdminRescuers() {
  const [data, setData] = useState<AdminPage<AdminRescuer> | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const load = useCallback(async (term: string) => {
    try {
      const query = term.trim() ? `?search=${encodeURIComponent(term.trim())}` : "";
      setData(await api<AdminPage<AdminRescuer>>(`/api/v1/admin/rescuers${query}`));
      setError("");
    } catch (reason) {
      setError(reason instanceof ApiError && (reason.status === 401 || reason.status === 403) ? "An administrator account is required." : reason instanceof Error ? reason.message : "Unable to load applications.");
    }
  }, []);
  useEffect(() => { void load(""); }, [load]);

  async function organizationAction(item: AdminRescuer) {
    if (!item.organization_id) return;
    setBusy(item.id);
    try {
      await api(`/api/v1/admin/organizations/${item.organization_id}/verification`, {method: "PATCH", body: JSON.stringify({status: "VERIFIED", note: "Verified by administrator after evidence review."})});
      await load(search);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Organization update failed."); }
    finally { setBusy(""); }
  }

  async function statusAction(item: AdminRescuer, status: string) {
    setBusy(item.id);
    try {
      await api(`/api/v1/admin/rescuers/${item.id}/verification`, {method: "PATCH", body: JSON.stringify({status, organization_id: item.organization_id, note: `Administrator set demo verification to ${status}.`})});
      await load(search);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Verification update failed."); }
    finally { setBusy(""); }
  }

  function searchNow(event: FormEvent) { event.preventDefault(); void load(search); }
  return <div className="space-y-6"><div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">ADMIN DEMO REVIEW — application status does not replace legal wildlife authorization and cannot enable authorized operation mode.</div><form className="card flex flex-col gap-3 sm:flex-row" onSubmit={searchNow}><input className="field mt-0" maxLength={100} placeholder="Name, email or authorization reference" value={search} onChange={(event) => setSearch(event.target.value)}/><Button type="submit">Search applications</Button></form>{error && <p className="card border-red-200 text-sm font-semibold text-danger" role="alert">{error}</p>}{data && !data.items.length && <div className="card text-center text-slate-600">No rescuer applications match.</div>}{data?.items.map((item) => <article className="card" key={item.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">{humanize(item.verification_status)}</p><h2 className="mt-2 text-xl font-black">{item.public_display_name || item.full_name}</h2><p className="mt-1 text-sm text-slate-600">{item.organization} · organization {humanize(item.organization_status || "unverified")}</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-900">DEMO APPLICATION</span></div><dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3"><div><dt className="font-bold text-slate-500">Private applicant contact</dt><dd className="mt-1">{item.email}<br/>{item.phone}</dd></div><div><dt className="font-bold text-slate-500">Authorization evidence</dt><dd className="mt-1">{item.authorization_reference}<br/>{item.issuing_authority}<br/>expires {item.authorization_expiry || "—"}</dd></div><div><dt className="font-bold text-slate-500">Evidence files</dt><dd className="mt-1">{item.document_count} private file{item.document_count === 1 ? "" : "s"}</dd></div></dl><div className="mt-6 flex flex-wrap gap-3">{item.organization_status !== "VERIFIED" && <Button type="button" disabled={busy === item.id} onClick={() => void organizationAction(item)}>Verify demo organization</Button>}{["PENDING", "PENDING_VERIFICATION", "REJECTED", "SUSPENDED", "EXPIRED"].includes(item.verification_status) && <Button type="button" disabled={busy === item.id} onClick={() => void statusAction(item, "UNDER_REVIEW")}>Move under review</Button>}{item.verification_status === "UNDER_REVIEW" && <><Button type="button" disabled={busy === item.id} onClick={() => void statusAction(item, "VERIFIED")}>Approve demo profile</Button><Button type="button" className="bg-slate-700" disabled={busy === item.id} onClick={() => void statusAction(item, "REJECTED")}>Reject</Button></>}{item.verification_status === "VERIFIED" && <Button type="button" className="bg-slate-700" disabled={busy === item.id} onClick={() => void statusAction(item, "SUSPENDED")}>Suspend</Button>}<a className="inline-flex rounded-xl border border-forest px-5 py-3 text-sm font-bold text-forest" href={`${API_URL}/api/v1/admin/rescuers/${item.id}/documents`} target="_blank" rel="noreferrer">Review document metadata</a></div></article>)}</div>;
}

type AdminBooking = {id: string; booking_reference: string; rescuer_id: string; state_code: string | null; district_code: string | null; status: string; payment_status: string; is_demo: boolean; created_at: string; expires_at: string};

export function AdminBookings() {
  const [data, setData] = useState<AdminPage<AdminBooking> | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      const query = status ? `?status=${encodeURIComponent(status)}` : "";
      setData(await api<AdminPage<AdminBooking>>(`/api/v1/admin/bookings${query}`));
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load bookings."); }
  }, [status]);
  useEffect(() => { void load(); }, [load]);
  return <div className="space-y-6"><div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">DEMO BOOKINGS ONLY — no live dispatch, external message, charge or transfer is represented here.</div><div className="card"><label><span className="label">Filter by status</span><select className="field max-w-md" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All demo bookings</option>{["PENDING_RESCUER_RESPONSE", "ACCEPTED", "REJECTED", "EXPIRED", "CANCELLED"].map((item) => <option key={item}>{item}</option>)}</select></label></div>{error && <p className="card border-red-200 text-danger" role="alert">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[780px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Reference</th><th>Area codes</th><th>Status</th><th>Payment</th><th>Created</th></tr></thead><tbody>{data?.items.map((item) => <tr className="border-b last:border-0" key={item.id}><td className="py-4 font-bold text-forest">{item.booking_reference}</td><td>{item.state_code || "—"} / {item.district_code || "—"}</td><td>{humanize(item.status)}</td><td>{humanize(item.payment_status)}</td><td>{formatDate(item.created_at)}</td></tr>)}</tbody></table>{data && !data.items.length && <p className="py-8 text-center text-slate-600">No demo bookings match.</p>}<p className="mt-5 text-xs text-slate-500">This list deliberately excludes customer contact details, exact coordinates and narrative notes.</p></section></div>;
}

type LocationOverview = {counts: Record<string, number>; imports: Array<{id: string; entity_type: string; source_url: string; source_version: string; source_filename: string; status: string; rows_received: number; rows_inserted: number; rows_updated: number; rows_skipped: number; error_summary: string | null; started_at: string}>; coverage_complete: false; coverage_note: string};

export function AdminLocations() {
  const [data, setData] = useState<LocationOverview | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<LocationOverview>("/api/v1/admin/locations").then(setData).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load import status.")); }, []);
  if (error) return <div className="card border-red-200 text-danger" role="alert">{error}</div>;
  if (!data) return <div className="card" role="status">Loading LGD import status…</div>;
  return <div className="space-y-6"><div className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-sm leading-6 text-amber-950"><strong>Coverage is not assumed complete.</strong> {data.coverage_note}</div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(data.counts).map(([label, count]) => <div className="card" key={label}><p className="text-sm font-bold text-slate-500">{humanize(label)}</p><p className="mt-2 text-4xl font-black text-forest">{count}</p></div>)}</div><section className="card overflow-x-auto"><h2 className="text-xl font-black">Import jobs</h2>{data.imports.length ? <table className="mt-5 w-full min-w-[900px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Entity</th><th>Source version</th><th>Status</th><th>Rows</th><th>Result</th></tr></thead><tbody>{data.imports.map((job) => <tr className="border-b last:border-0" key={job.id}><td className="py-4 font-bold">{humanize(job.entity_type)}</td><td>{job.source_version}<br/><span className="text-xs text-slate-500">{job.source_filename}</span></td><td>{job.status}</td><td>{job.rows_received}</td><td>{job.rows_inserted} inserted · {job.rows_updated} updated · {job.rows_skipped} unchanged{job.error_summary && <span className="block text-danger">{job.error_summary}</span>}</td></tr>)}</tbody></table> : <p className="mt-5 rounded-xl bg-mist p-8 text-center text-slate-600">No official LGD export has been imported.</p>}</section><div className="card text-sm leading-6"><h2 className="font-black">Operator command</h2><p className="mt-2">Download official CSV/XLSX exports from the Government of India LGD Download Directory, verify the export date, then run the documented `python -m app.db.import_lgd` command. This dashboard does not fetch around LGD CAPTCHA or invent missing areas.</p></div></div>;
}

type DeliveryRow = {id:string;event_type:string;booking_id:string|null;channel:string;provider:string;status:string;attempt_count:number;max_attempts:number;sanitized_result:string|null;created_at:string};

export function AdminNotificationDeliveries() {
  const [data,setData]=useState<AdminPage<DeliveryRow>|null>(null);const[error,setError]=useState("");
  useEffect(()=>{api<AdminPage<DeliveryRow>>("/api/v1/admin/notifications").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load notification delivery status."));},[]);
  return <div className="space-y-6"><div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">SANITIZED DEMO DELIVERY LOG — recipients, device tokens, credentials, and full message bodies are excluded.</div>{error&&<p className="card border-red-200 text-danger" role="alert">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Event</th><th>Channel</th><th>Provider</th><th>Status</th><th>Attempts</th><th>Result</th></tr></thead><tbody>{data?.items.map((item)=><tr className="border-b last:border-0" key={item.id}><td className="py-4 font-bold">{humanize(item.event_type)}</td><td>{item.channel}</td><td>{item.provider}</td><td>{humanize(item.status)}</td><td>{item.attempt_count}/{item.max_attempts}</td><td>{item.sanitized_result||"—"}</td></tr>)}</tbody></table>{data&&!data.items.length&&<p className="py-8 text-center text-slate-600">No notification deliveries recorded.</p>}</section></div>;
}

type TrackingRow={id:string;booking_reference:string;status:string;started_at:string;last_location_at:string|null;expires_at:string;is_demo:boolean};

export function AdminTrackingSessions(){
 const[data,setData]=useState<AdminPage<TrackingRow>|null>(null);const[error,setError]=useState("");
 useEffect(()=>{api<AdminPage<TrackingRow>>("/api/v1/admin/tracking").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load tracking status."));},[]);
 return <div className="space-y-6"><div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">DEMO TRACKING STATUS ONLY — exact movement coordinates are intentionally absent from this administrator list.</div>{error&&<p className="card border-red-200 text-danger">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Booking</th><th>Status</th><th>Started</th><th>Last point</th><th>Expires</th></tr></thead><tbody>{data?.items.map((item)=><tr className="border-b last:border-0" key={item.id}><td className="py-4 font-bold text-forest">{item.booking_reference}</td><td>{humanize(item.status)}</td><td>{formatDate(item.started_at)}</td><td>{item.last_location_at?formatDate(item.last_location_at):"None"}</td><td>{formatDate(item.expires_at)}</td></tr>)}</tbody></table>{data&&!data.items.length&&<p className="py-8 text-center text-slate-600">No demo tracking sessions.</p>}</section></div>;
}
