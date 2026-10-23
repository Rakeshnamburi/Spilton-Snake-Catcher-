"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {BellRing, CalendarClock, MapPin} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {formatDate, humanize, type Booking, type MarketplacePage} from "@/lib/marketplace";
import {useI18n} from "@/lib/i18n";
import {CustomerCompletionPanel} from "./day5-customer";

function BookingBadge({status}: {status: string}) {
  const terminal = ["REJECTED", "EXPIRED", "CANCELLED"].includes(status);
  return <span className={`rounded-full px-3 py-1 text-xs font-black ${terminal ? "bg-slate-200 text-slate-700" : "bg-emerald/10 text-forest"}`}>{humanize(status)}</span>;
}

export function MyBookings() {
  const {t} = useI18n();
  const [data, setData] = useState<MarketplacePage<Booking> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await api<MarketplacePage<Booking>>("/api/v1/bookings/mine"));
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401 ? "Sign in to view your protected demo bookings." : reason instanceof Error ? reason.message : "Unable to load bookings.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className="card" role="status">{t("booking.loading")}</div>;
  if (error) return <div className="card border-red-200" role="alert"><h2 className="font-black text-danger">{t("booking.unavailable")}</h2><p className="mt-2 text-sm">{error}</p><Link href="/login" className="mt-5 inline-block font-bold text-forest">{t("nav.signIn")}</Link></div>;
  if (!data?.items.length) return <div className="card text-center"><BellRing className="mx-auto text-forest"/><h2 className="mt-4 text-xl font-black">{t("booking.none")}</h2><p className="mt-2 text-sm text-slate-600">Browse the simulated directory to create a test request.</p><Link href="/rescuers" className="mt-5 inline-block rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white">{t("booking.browse")}</Link></div>;

  return <div className="space-y-5">{data.items.map((booking) => <article className="card" key={booking.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-black tracking-wide text-danger">DEMO BOOKING</p><h2 className="mt-2 text-xl font-black text-forest">{booking.booking_reference}</h2><p className="mt-1 text-sm text-slate-600">{booking.rescuer_display_name} · {booking.organization}</p></div><BookingBadge status={booking.status}/></div><div className="mt-5 grid gap-3 text-sm sm:grid-cols-2"><p className="flex items-center gap-2"><CalendarClock size={17}/>{formatDate(booking.created_at)}</p><p className="flex items-center gap-2"><MapPin size={17}/>LGD {booking.state_code ?? "—"} / {booking.district_code ?? "—"}</p></div><div className="mt-5"><Link className="font-bold text-forest" href={`/bookings/${booking.id}`}>View status and history →</Link></div></article>)}</div>;
}

export function BookingDetail({id, created = false}: {id: string; created?: boolean}) {
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setBooking(await api<Booking>(`/api/v1/bookings/${encodeURIComponent(id)}`));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load this protected booking.");
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => { void load(); }, [load]);

  async function cancel() {
    if (!booking || busy || !confirm("Cancel this simulated booking?")) return;
    setBusy(true);
    try {
      setBooking(await api<Booking>(`/api/v1/bookings/${booking.id}/cancel`, {method: "POST", body: JSON.stringify({note: "Cancelled by customer from web."})}));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Cancellation failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="card" role="status">Loading booking status…</div>;
  if (!booking) return <div className="card border-red-200" role="alert">{error || "Booking not found."}</div>;
  const cancellable = ["REQUESTED", "PENDING_RESCUER_RESPONSE", "ACCEPTED", "EN_ROUTE", "ARRIVED"].includes(booking.status);
  return <div className="space-y-7">
    {created && <div className="rounded-2xl border border-emerald bg-green-50 p-5 text-sm leading-6 text-forest"><strong>Simulated booking created.</strong> It is stored in the demo system only; no real rescuer was contacted.</div>}
    <section className="card"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">{booking.booking_reference}</p><h2 className="mt-2 text-3xl font-black">{booking.rescuer_display_name}</h2><p className="mt-1 text-sm text-slate-600">{booking.organization}</p></div><BookingBadge status={booking.status}/></div>{booking.status === "ARRIVED" && <p className="mt-5 rounded-xl bg-green-50 p-4 text-sm font-bold text-forest">Your assigned fictional demo rescuer marked the location as reached. GPS does not prove arrival with certainty.</p>}{booking.arrival_review_warning && <p className="mt-3 rounded-xl bg-amber-50 p-4 text-sm font-bold text-amber-900">Arrival location differed significantly from the customer-approved location. Review the record before confirming completion.</p>}<div className="mt-7 grid gap-5 sm:grid-cols-2"><div><p className="text-xs font-bold uppercase text-slate-500">Submitted</p><p className="mt-1">{formatDate(booking.created_at)}</p></div><div><p className="text-xs font-bold uppercase text-slate-500">Response expires</p><p className="mt-1">{formatDate(booking.expires_at)}</p></div><div><p className="text-xs font-bold uppercase text-slate-500">Location</p><p className="mt-1">{booking.manual_address ?? `${booking.latitude ?? "—"}, ${booking.longitude ?? "—"}`}</p></div><div><p className="text-xs font-bold uppercase text-slate-500">Financial status</p><p className="mt-1">Payments {humanize(booking.payment_status).toLowerCase()} · demo records only</p></div><div className="sm:col-span-2"><p className="text-xs font-bold uppercase text-slate-500">Situation details</p><p className="mt-1 leading-6">{booking.customer_notes}</p></div></div>{cancellable && <Button className="mt-7 bg-slate-700" type="button" disabled={busy} onClick={() => void cancel()}>{busy ? "Cancelling…" : "Cancel simulated booking"}</Button>}{error && <p className="mt-4 text-sm font-semibold text-danger" role="alert">{error}</p>}</section>
    <section className="card"><h2 className="text-xl font-black">Status timeline</h2><ol className="mt-6 space-y-5">{booking.history.map((entry) => <li className="border-l-2 border-emerald pl-5" key={entry.id}><div className="flex flex-wrap justify-between gap-2"><strong>{humanize(entry.status)}</strong><time className="text-xs text-slate-500">{formatDate(entry.created_at)}</time></div>{entry.note && <p className="mt-2 text-sm text-slate-600">{entry.note}</p>}</li>)}</ol></section>
    {["ACCEPTED", "EN_ROUTE", "ARRIVED"].includes(booking.status) && <Link className="inline-flex rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white" href={`/bookings/${booking.id}/tracking`}>Open protected demo tracking →</Link>}
    <CustomerCompletionPanel booking={booking} onRefresh={load}/>
    <div className="rounded-2xl bg-mist p-5 text-sm leading-6 text-slate-700"><strong>Privacy:</strong> exact customer location is owner-visible here. The assigned demo rescuer receives only an approximate destination. Foreground tracking starts only after explicit consent.</div>
  </div>;
}
