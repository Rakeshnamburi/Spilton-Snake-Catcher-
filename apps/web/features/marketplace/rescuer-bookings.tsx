"use client";

import {useCallback, useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {formatDate, humanize, type Booking, type MarketplacePage} from "@/lib/marketplace";

export function RescuerBookings() {
  const [data, setData] = useState<MarketplacePage<Booking> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const load = useCallback(async () => {
    try {
      setData(await api<MarketplacePage<Booking>>("/api/v1/bookings/assigned"));
      setError("");
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 403 ? "A verified RESCUER account is required." : reason instanceof Error ? reason.message : "Unable to load assigned requests.");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function respond(booking: Booking, action: "accept" | "reject") {
    setBusy(booking.id);
    setError("");
    try {
      await api(`/api/v1/bookings/${booking.id}/${action}`, {method: "POST", body: JSON.stringify({note: `Simulated ${action} action from rescuer dashboard.`})});
      await load();
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 409 ? "This request changed before your response. The list has been refreshed." : reason instanceof Error ? reason.message : "Response failed.");
      await load();
    } finally {
      setBusy("");
    }
  }

  if (!data && !error) return <div className="card" role="status">Loading incoming demo requests…</div>;
  return <div className="space-y-5"><div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">Accept and reject actions are simulations only. Customer contact details and exact coordinates are not disclosed in this Day 3 workspace.</div>{error && <p className="card border-red-200 text-sm font-semibold text-danger" role="alert">{error}</p>}{data && !data.items.length && <div className="card text-center text-slate-600">No assigned demo booking requests.</div>}{data?.items.map((booking) => <article className="card" key={booking.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">{booking.booking_reference}</p><h2 className="mt-2 text-xl font-black">{humanize(booking.status)}</h2><p className="mt-2 text-sm text-slate-600">Created {formatDate(booking.created_at)}</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-900">DEMO ONLY</span></div><div className="mt-5 grid gap-4 sm:grid-cols-2"><div><p className="text-xs font-bold uppercase text-slate-500">Approximate location</p><p className="mt-1">{booking.latitude ?? "Manual"}, {booking.longitude ?? "location"}</p></div><div><p className="text-xs font-bold uppercase text-slate-500">Directory coverage</p><p className="mt-1">{booking.state_code} / {booking.district_code}</p></div><div className="sm:col-span-2"><p className="text-xs font-bold uppercase text-slate-500">Customer-approved situation details</p><p className="mt-1 leading-6">{booking.customer_notes}</p></div></div>{booking.status === "PENDING_RESCUER_RESPONSE" && <div className="mt-6 flex flex-wrap gap-3"><Button type="button" disabled={busy === booking.id} onClick={() => void respond(booking, "accept")}>Accept simulation</Button><Button type="button" disabled={busy === booking.id} className="bg-slate-700" onClick={() => void respond(booking, "reject")}>Reject simulation</Button></div>}</article>)}</div>;
}
