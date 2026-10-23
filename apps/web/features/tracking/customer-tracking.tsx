"use client";

import Link from "next/link";
import {useCallback, useEffect, useRef, useState} from "react";
import {Clock3, Radio, RefreshCw, ShieldAlert} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api, API_URL} from "@/lib/api";
import {formatDate, humanize, type Booking, type BookingEventPage, type BookingTracking} from "@/lib/marketplace";
import {TrackingMap} from "./tracking-map";

export function CustomerTracking({id}: {id: string}) {
  const [booking, setBooking] = useState<Booking | null>(null);
  const [tracking, setTracking] = useState<BookingTracking | null>(null);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(true);
  const [connection, setConnection] = useState<"CONNECTING" | "LIVE" | "POLLING" | "OFFLINE">("CONNECTING");
  const sequence = useRef(0);
  const load = useCallback(async () => {
    try {
      const [nextBooking, nextTracking, events] = await Promise.all([
        api<Booking>(`/api/v1/bookings/${encodeURIComponent(id)}`),
        api<BookingTracking>(`/api/v1/bookings/${encodeURIComponent(id)}/tracking`),
        api<BookingEventPage>(`/api/v1/bookings/${encodeURIComponent(id)}/events?after_sequence=${sequence.current}`),
      ]);
      setBooking(nextBooking);
      setTracking(nextTracking);
      setStale(!nextTracking.last_location_at || Date.now() - new Date(nextTracking.last_location_at).getTime() > 30_000);
      sequence.current = Math.max(sequence.current, events.last_sequence);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Tracking status is unavailable.");
      setConnection("OFFLINE");
    }
  }, [id]);

  useEffect(() => {
    void load();
    const poll = window.setInterval(() => {
      setConnection((value) => value === "LIVE" ? value : "POLLING");
      void load();
    }, 10_000);
    const stream = new EventSource(
      `${API_URL}/api/v1/bookings/${encodeURIComponent(id)}/events/stream?after_sequence=${sequence.current}`,
      {withCredentials: true},
    );
    stream.onopen = () => setConnection("LIVE");
    stream.onmessage = () => void load();
    stream.onerror = () => setConnection("POLLING");
    return () => { window.clearInterval(poll); stream.close(); };
  }, [id, load]);

  const rescuer = tracking?.latest_location ? {latitude: tracking.latest_location.latitude, longitude: tracking.latest_location.longitude} : null;
  const destination = tracking?.destination_latitude != null && tracking.destination_longitude != null ? {latitude: tracking.destination_latitude, longitude: tracking.destination_longitude} : null;

  if (!booking || !tracking) return <div className="card" role="status">{error || "Loading protected demo tracking…"}</div>;
  return <div className="space-y-6">
    <div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">SIMULATED DEMO TRACKING — not an active emergency rescue service. For suspected snakebite, seek immediate medical care and call 112.</div>
    <section className="grid gap-4 sm:grid-cols-4">
      <div className="card sm:col-span-2"><p className="eyebrow">{booking.booking_reference}</p><h2 className="mt-2 text-2xl font-black">{booking.rescuer_display_name}</h2><p className="mt-1 text-sm text-slate-600">Verified demo profile · {booking.organization}</p></div>
      <div className="card"><p className="text-xs font-black uppercase text-slate-500">Journey</p><p className="mt-2 text-xl font-black text-forest">{humanize(booking.status)}</p></div>
      <div className="card"><p className="flex items-center gap-2 text-xs font-black uppercase text-slate-500"><Radio size={16}/>Connection</p><p className="mt-2 text-xl font-black text-forest">{humanize(connection)}</p></div>
    </section>
    {stale && <div className="flex gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><ShieldAlert className="shrink-0"/><p><strong>Not live right now.</strong> {tracking.last_location_at ? `The last simulated point was ${formatDate(tracking.last_location_at)}.` : "No simulated location has been shared."}</p></div>}
    <TrackingMap rescuer={rescuer} destination={destination} route={tracking.route.coordinates}/>
    <section className="card grid gap-5 sm:grid-cols-3"><div><p className="text-xs font-black uppercase text-slate-500">Tracking status</p><p className="mt-2 font-bold">{tracking.status ? humanize(tracking.status) : "Not started"}</p></div><div><p className="text-xs font-black uppercase text-slate-500">Last update</p><p className="mt-2 font-bold">{tracking.last_location_at ? formatDate(tracking.last_location_at) : "Unavailable"}</p></div><div><p className="text-xs font-black uppercase text-slate-500">ETA</p><p className="mt-2 font-bold">{tracking.route.eta_at ? formatDate(tracking.route.eta_at) : "Unavailable"}</p></div><div className="sm:col-span-3 rounded-xl bg-mist p-4 text-sm leading-6"><strong>Route:</strong> {tracking.route.message}{tracking.route.road_distance_km != null ? ` Road estimate ${tracking.route.road_distance_km} km.` : tracking.route.geographic_distance_km != null ? ` Geographic distance ${tracking.route.geographic_distance_km} km (not road distance).` : ""}</div></section>
    {error && <p className="card border-red-200 text-sm font-semibold text-danger" role="alert">{error}</p>}
    <div className="flex flex-wrap gap-3"><Button type="button" onClick={() => void load()}><RefreshCw size={17}/>Refresh</Button><Link className="inline-flex items-center gap-2 rounded-xl border border-forest px-5 py-3 text-sm font-bold text-forest" href={`/bookings/${booking.id}`}><Clock3 size={17}/>Booking timeline</Link></div>
  </div>;
}
