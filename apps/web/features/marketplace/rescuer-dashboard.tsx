"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {Activity, BellRing, ShieldCheck} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {humanize, type AvailabilityStatus} from "@/lib/marketplace";

type Application = {
  id: string;
  public_display_name: string | null;
  organization_name: string | null;
  verification_status: string;
  availability: AvailabilityStatus;
  authorization_expiry: string | null;
  service_area_description: string;
  is_demo: boolean;
};
type Notification = {id: string; title: string; body: string; created_at: string; read_at: string | null};

export function RescuerDashboard() {
  const [profile, setProfile] = useState<Application | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const [application, inbox] = await Promise.all([
        api<Application>("/api/v1/rescuers/me"),
        api<Notification[]>("/api/v1/notifications/mine?limit=10").catch(() => []),
      ]);
      setProfile(application);
      setNotifications(inbox);
      setError("");
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 404 ? "No rescuer application exists for this account." : reason instanceof Error ? reason.message : "Dashboard unavailable.");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function availability(status: AvailabilityStatus) {
    setBusy(true);
    try {
      setProfile(await api<Application>("/api/v1/rescuers/me/availability", {method: "PATCH", body: JSON.stringify({status})}));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Availability update failed.");
    } finally {
      setBusy(false);
    }
  }

  if (!profile && !error) return <div className="card" role="status">Loading rescuer dashboard…</div>;
  if (!profile) return <div className="card border-red-200" role="alert"><p>{error}</p><Link className="mt-5 inline-block font-bold text-forest" href="/rescuer/register">Start demo onboarding</Link></div>;
  const verified = profile.verification_status === "VERIFIED";
  return <div className="space-y-7">
    <div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">SIMULATED RESCUER WORKSPACE — availability and booking actions never authorize real dispatch.</div>
    <div className="grid gap-5 md:grid-cols-3"><div className="card"><ShieldCheck className="text-forest"/><p className="mt-4 text-sm font-bold text-slate-500">Verification</p><p className="mt-1 text-xl font-black">{humanize(profile.verification_status)}</p></div><div className="card"><Activity className="text-forest"/><p className="mt-4 text-sm font-bold text-slate-500">Demo availability</p><p className="mt-1 text-xl font-black">{humanize(profile.availability)}</p></div><div className="card"><p className="text-sm font-bold text-slate-500">Service area</p><p className="mt-2 text-sm leading-6">{profile.service_area_description}</p></div></div>
    <section className="card"><h2 className="text-xl font-black">Availability controls</h2><p className="mt-2 text-sm text-slate-600">AVAILABLE profiles automatically become OFFLINE after a stale session. ACCEPTED demo bookings set the profile to BUSY.</p><div className="mt-5 flex flex-wrap gap-3">{(["AVAILABLE", "BUSY", "OFFLINE"] as AvailabilityStatus[]).map((status) => <Button key={status} type="button" disabled={busy || !verified || profile.availability === status} className={status === "OFFLINE" ? "bg-slate-700" : ""} onClick={() => void availability(status)}>{humanize(status)}</Button>)}</div>{!verified && <p className="mt-4 text-sm font-semibold text-amber-800">Availability is locked until an administrator verifies the application and organization evidence.</p>}{error && <p className="mt-4 text-sm font-semibold text-danger" role="alert">{error}</p>}</section>
    <section className="card"><div className="flex items-center gap-3"><BellRing className="text-forest"/><h2 className="text-xl font-black">In-app demo notifications</h2></div>{notifications.length ? <ul className="mt-5 divide-y">{notifications.map((item) => <li className="py-4" key={item.id}><strong>{item.title}</strong><p className="mt-1 text-sm text-slate-600">{item.body}</p></li>)}</ul> : <p className="mt-5 text-sm text-slate-600">No in-app demo notifications.</p>}</section>
    <Link className="inline-flex rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white" href="/rescuer/bookings">Open incoming demo requests</Link>
  </div>;
}
