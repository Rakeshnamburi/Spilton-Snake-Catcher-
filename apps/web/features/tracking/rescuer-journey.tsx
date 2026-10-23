"use client";

import {useCallback, useEffect, useRef, useState} from "react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";
import {formatDate, humanize, type Booking, type BookingTracking} from "@/lib/marketplace";
import {TrackingMap} from "./tracking-map";
import {RescuerCompletionPanel} from "@/features/marketplace/day5-rescuer";

export function RescuerJourney({id}: {id: string}) {
  const [booking, setBooking] = useState<Booking | null>(null);
  const [tracking, setTracking] = useState<BookingTracking | null>(null);
  const [consent, setConsent] = useState(false);
  const [manual, setManual] = useState({latitude: "", longitude: ""});
  const [message, setMessage] = useState("");
  const [sharing, setSharing] = useState(false);
  const [busy, setBusy] = useState(false);
  const watchId = useRef<number | null>(null);
  const lastSent = useRef(0);
  const load = useCallback(async () => {
    const [nextBooking, nextTracking] = await Promise.all([
      api<Booking>(`/api/v1/bookings/${encodeURIComponent(id)}`),
      api<BookingTracking>(`/api/v1/bookings/${encodeURIComponent(id)}/tracking`),
    ]);
    setBooking(nextBooking); setTracking(nextTracking);
  }, [id]);
  useEffect(() => { void load().catch((reason) => setMessage(reason instanceof Error ? reason.message : "Journey unavailable.")); }, [load]);
  const stopWatcher = useCallback(() => {
    if (watchId.current != null) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    setSharing(false);
  }, []);
  useEffect(() => stopWatcher, [stopWatcher]);
  useEffect(() => {
    function handleVisibility() {
      if (document.visibilityState === "hidden" && watchId.current != null) {
        stopWatcher();
        setMessage("Browser tab is inactive, so continuous foreground updates stopped. Resume explicitly when you return.");
      }
    }
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [stopWatcher]);

  async function sendLocation(latitude: number, longitude: number, accuracy: number) {
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      setMessage("Enter valid synthetic latitude and longitude values.");
      return;
    }
    if (Date.now() - lastSent.current < 10_000) return;
    lastSent.current = Date.now();
    try {
      setTracking(await api<BookingTracking>(`/api/v1/bookings/${id}/tracking/location`, {method: "POST", body: JSON.stringify({latitude, longitude, accuracy, recorded_at: new Date().toISOString(), is_simulated: true})}));
      setMessage("Private simulated foreground point updated.");
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Location update failed."); }
  }

  function startBrowserWatcher() {
    if (!navigator.geolocation) { setMessage("Browser GPS is unavailable. Use synthetic manual coordinates."); return; }
    stopWatcher();
    watchId.current = navigator.geolocation.watchPosition(
      (position) => void sendLocation(position.coords.latitude, position.coords.longitude, position.coords.accuracy),
      (error) => setMessage(error.code === error.PERMISSION_DENIED ? "Location permission denied. Manual synthetic coordinates remain available." : "GPS is temporarily unavailable."),
      {enableHighAccuracy: true, maximumAge: 5_000, timeout: 10_000},
    );
    setSharing(true);
  }

  async function action(path: string) {
    setBusy(true); setMessage("");
    try {
      const result = await api<BookingTracking>(`/api/v1/bookings/${id}/${path}`, {method: "POST", body: path === "tracking/start" ? JSON.stringify({consent: true, disclosure_version: "day4-demo-v1"}) : undefined});
      setTracking(result); await load();
      if (path === "tracking/pause" || path === "tracking/stop" || path === "arrived") stopWatcher();
      if (path === "tracking/start" || path === "tracking/resume") startBrowserWatcher();
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Action failed."); }
    finally { setBusy(false); }
  }

  if (!booking || !tracking) return <div className="card" role="status">{message || "Loading assigned demo journey…"}</div>;
  const rescuer = tracking.latest_location ? {latitude: tracking.latest_location.latitude, longitude: tracking.latest_location.longitude} : null;
  const destination = tracking.destination_latitude != null && tracking.destination_longitude != null ? {latitude: tracking.destination_latitude, longitude: tracking.destination_longitude} : null;
  return <div className="space-y-6">
    <div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">FOREGROUND DEMO TRACKING ONLY — location sharing never starts automatically and stops when you pause, stop, arrive, cancel, or leave this page.</div>
    <section className="card"><p className="eyebrow">{booking.booking_reference}</p><div className="mt-3 flex flex-wrap items-center justify-between gap-3"><h2 className="text-2xl font-black">{humanize(booking.status)}</h2><span className="rounded-full bg-emerald/10 px-3 py-1 text-xs font-black text-forest">Tracking {tracking.status ? humanize(tracking.status) : "not started"}</span></div><p className="mt-4 text-sm text-slate-600">Customer-approved approximate destination: {booking.latitude ?? "manual"}, {booking.longitude ?? "location"}</p></section>
    {booking.status === "ACCEPTED" && <section className="card"><h3 className="text-xl font-black">Start simulated journey</h3><label className="mt-4 flex items-start gap-3 text-sm leading-6"><input className="mt-1 h-5 w-5" type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)}/><span>I explicitly consent to share foreground location for this demo session. I understand no background tracking or live dispatch occurs.</span></label><Button className="mt-5" type="button" disabled={!consent || busy} onClick={() => void action("tracking/start")}>Start with browser GPS</Button></section>}
    {tracking.status === "ACTIVE" && <div className="flex flex-wrap gap-3"><Button disabled={busy} onClick={() => void action("tracking/pause")}>Pause sharing</Button><Button className="bg-slate-700" disabled={busy} onClick={() => void action("tracking/stop")}>Stop sharing</Button><Button className="bg-emerald" disabled={busy} onClick={() => void action("arrived")}>Mark simulated arrival</Button></div>}
    {tracking.status === "PAUSED" && <div className="flex flex-wrap gap-3"><Button disabled={busy} onClick={() => void action("tracking/resume")}>Resume sharing</Button><Button className="bg-slate-700" disabled={busy} onClick={() => void action("tracking/stop")}>Stop sharing</Button></div>}
    {tracking.status === "ACTIVE" && <section className="card"><h3 className="font-black">Synthetic manual point fallback</h3><p className="mt-2 text-sm text-slate-600">Use fictional test coordinates only when browser permission is denied.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><input className="field mt-0" inputMode="decimal" aria-label="Synthetic latitude" placeholder="Latitude" value={manual.latitude} onChange={(event) => setManual({...manual, latitude: event.target.value})}/><input className="field mt-0" inputMode="decimal" aria-label="Synthetic longitude" placeholder="Longitude" value={manual.longitude} onChange={(event) => setManual({...manual, longitude: event.target.value})}/></div><Button className="mt-4" type="button" onClick={() => void sendLocation(Number(manual.latitude), Number(manual.longitude), 25)}>Send synthetic point</Button></section>}
    <TrackingMap rescuer={rescuer} destination={destination} route={tracking.route.coordinates}/>
    <section className="card grid gap-4 text-sm sm:grid-cols-3"><p><strong>GPS accuracy</strong><br/>{tracking.latest_location ? `±${Math.round(tracking.latest_location.accuracy)} m` : "Unavailable"}</p><p><strong>Last successful update</strong><br/>{tracking.last_location_at ? formatDate(tracking.last_location_at) : "None"}</p><p><strong>Connection</strong><br/>{sharing ? "Foreground GPS requested" : "Not continuously sharing"}</p></section>
    <RescuerCompletionPanel booking={booking} onRefresh={load}/>
    {message && <p className="card border-amber-200 text-sm font-semibold" role="status">{message}</p>}
  </div>;
}
