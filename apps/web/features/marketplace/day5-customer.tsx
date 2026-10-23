"use client";

import {FormEvent, useCallback, useEffect, useState} from "react";
import {CheckCircle2, FileImage, IndianRupee, ShieldAlert, Star} from "lucide-react";
import type {DemoPayment, RescueEvidence, RescueReport} from "@spilton/shared-types";
import {Button} from "@/components/ui/button";
import {api, ApiError, API_URL} from "@/lib/api";
import {formatDate, humanize, type Booking} from "@/lib/marketplace";

function requestKey(prefix: string) {
  return prefix + "-" + crypto.randomUUID();
}

export function CustomerCompletionPanel({
  booking,
  onRefresh,
}: {
  booking: Booking;
  onRefresh: () => Promise<void>;
}) {
  const [report, setReport] = useState<RescueReport | null>(null);
  const [evidence, setEvidence] = useState<RescueEvidence[]>([]);
  const [payment, setPayment] = useState<DemoPayment | null>(null);
  const [method, setMethod] =
    useState<"DEMO_ONLINE" | "DEMO_CASH" | "NO_CHARGE">("NO_CHARGE");
  const [amount, setAmount] = useState("0.00");
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState("");
  const [disputeReason, setDisputeReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!["COMPLETED", "UNABLE_TO_ASSIST", "DISPUTED"].includes(booking.status)) return;
    const [nextReport, nextEvidence, payments] = await Promise.all([
      api<RescueReport>("/api/v1/bookings/" + booking.id + "/rescue/report").catch(
        (reason) => {
          if (reason instanceof ApiError && reason.status === 404) return null;
          throw reason;
        },
      ),
      api<RescueEvidence[]>("/api/v1/bookings/" + booking.id + "/rescue/evidence"),
      api<DemoPayment[]>("/api/v1/payments"),
    ]);
    setReport(nextReport);
    setEvidence(nextEvidence);
    setPayment(payments.find((item) => item.booking_id === booking.id) ?? null);
  }, [booking.id, booking.status]);

  useEffect(() => {
    void load().catch((reason) =>
      setMessage(reason instanceof Error ? reason.message : "Completion details unavailable."),
    );
  }, [load]);

  async function confirmCompletion() {
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + booking.id + "/confirm-completion", {method: "POST"});
      setMessage("You confirmed this simulated completion.");
      await onRefresh();
      await load();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Confirmation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createPayment(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const created = await api<DemoPayment>("/api/v1/bookings/" + booking.id + "/payments", {
        method: "POST",
        headers: {"Idempotency-Key": requestKey("web-payment")},
        body: JSON.stringify({
          method,
          amount: method === "NO_CHARGE" ? "0.00" : amount,
          currency: "INR",
          confirm_demo: true,
        }),
      });
      if (created.method === "DEMO_ONLINE") {
        setPayment(
          await api<DemoPayment>("/api/v1/payments/" + created.id + "/confirm", {
            method: "POST",
            body: JSON.stringify({simulate_failure: false}),
          }),
        );
      } else {
        setPayment(created);
      }
      setMessage("Demo financial record saved. No real money moved.");
      await onRefresh();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Demo payment failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitReview(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + booking.id + "/review", {
        method: "POST",
        body: JSON.stringify({rating, review_text: reviewText || null}),
      });
      setMessage("Demo review published.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Review could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function dispute(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + booking.id + "/dispute", {
        method: "POST",
        body: JSON.stringify({reason: disputeReason}),
      });
      setMessage("The simulated completion dispute was opened for admin review.");
      await onRefresh();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Dispute could not be opened.");
    } finally {
      setBusy(false);
    }
  }

  async function openEvidence(item: RescueEvidence) {
    const response = await fetch(
      API_URL + "/api/v1/bookings/" + booking.id + "/rescue/evidence/" + item.id,
      {credentials: "include"},
    );
    if (!response.ok) {
      setMessage("Evidence access was denied or the retained file is unavailable.");
      return;
    }
    const url = URL.createObjectURL(await response.blob());
    window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }

  if (!["COMPLETED", "UNABLE_TO_ASSIST", "DISPUTED"].includes(booking.status)) return null;
  return <div className="space-y-6">
    <section className="card">
      <div className="flex items-center gap-3">
        <CheckCircle2 className="text-emerald"/>
        <h2 className="text-xl font-black">Simulated rescue outcome</h2>
      </div>
      {report ? <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
        <div><p className="font-bold text-slate-500">Outcome</p><p>{report.outcome_label}</p></div>
        <div><p className="font-bold text-slate-500">Recorded</p><p>{formatDate(report.completed_at)}</p></div>
        <div className="sm:col-span-2"><p className="font-bold text-slate-500">Observations</p><p className="leading-6">{report.observations}</p></div>
        <div className="sm:col-span-2"><p className="font-bold text-slate-500">Authorized action record</p><p className="leading-6">{report.authorized_action_summary}</p></div>
        {report.species_text && <div className="sm:col-span-2 rounded-xl bg-amber-50 p-4"><strong>Unverified species note:</strong> {report.species_text}. This is not a safety classification.</div>}
      </div> : <p className="mt-4 text-sm text-slate-600">No completion report is available.</p>}
      {booking.status === "COMPLETED" && !booking.customer_confirmed_at && <Button className="mt-6" disabled={busy} onClick={() => void confirmCompletion()}>Confirm simulated completion</Button>}
      {booking.customer_confirmed_at && <p className="mt-5 font-bold text-forest">Confirmed {formatDate(booking.customer_confirmed_at)}</p>}
    </section>

    <section className="card">
      <div className="flex items-center gap-3"><FileImage className="text-forest"/><h2 className="text-xl font-black">Private evidence</h2></div>
      <p className="mt-2 text-sm text-slate-600">Images are access-controlled and temporarily retained. Exact evidence coordinates are never shown here.</p>
      <div className="mt-4 space-y-3">{evidence.length ? evidence.map((item) => <button className="flex w-full items-center justify-between rounded-xl border p-4 text-left" key={item.id} type="button" onClick={() => void openEvidence(item)}><span><strong>{item.original_filename}</strong><span className="block text-xs text-slate-500">{humanize(item.evidence_type)} · {Math.round(item.file_size / 1024)} KB</span></span><span className="font-bold text-forest">View</span></button>) : <p className="rounded-xl bg-mist p-4 text-sm">No optional evidence was attached.</p>}</div>
    </section>

    {booking.customer_confirmed_at && !payment && <form className="card" onSubmit={createPayment}>
      <div className="flex items-center gap-3"><IndianRupee className="text-forest"/><h2 className="text-xl font-black">Demo payment choice</h2></div>
      <p className="mt-2 text-sm text-danger"><strong>Simulation only.</strong> No card, UPI, bank details, charge, or payout is processed.</p>
      <label className="mt-5 block"><span className="label">Method</span><select className="field" value={method} onChange={(event) => {const value = event.target.value as typeof method; setMethod(value); if (value === "NO_CHARGE") setAmount("0.00");}}><option value="NO_CHARGE">No charge</option><option value="DEMO_ONLINE">Simulate online success</option><option value="DEMO_CASH">Demo cash awaiting rescuer confirmation</option></select></label>
      {method !== "NO_CHARGE" && <label className="mt-4 block"><span className="label">Illustrative amount (INR)</span><input className="field" inputMode="decimal" required value={amount} onChange={(event) => setAmount(event.target.value)}/></label>}
      <Button className="mt-5" disabled={busy} type="submit">Save demo financial record</Button>
    </form>}
    {payment && <section className="card"><h2 className="text-xl font-black">Demo receipt</h2><dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-bold text-slate-500">Reference</dt><dd>{payment.payment_reference}</dd></div><div><dt className="font-bold text-slate-500">Status</dt><dd>{humanize(payment.status)}</dd></div><div><dt className="font-bold text-slate-500">Illustrative amount</dt><dd>₹{payment.amount}</dd></div><div><dt className="font-bold text-slate-500">Commission snapshot</dt><dd>{payment.commission_amount ? "₹" + payment.commission_amount : "Not applicable"}</dd></div></dl><p className="mt-4 text-xs text-danger">Not a tax invoice. No real money was collected or transferred.</p></section>}

    {booking.customer_confirmed_at && <form className="card" onSubmit={submitReview}><div className="flex items-center gap-3"><Star className="text-amber-500"/><h2 className="text-xl font-black">Review this demo workflow</h2></div><label className="mt-5 block"><span className="label">Rating</span><select className="field" value={rating} onChange={(event) => setRating(Number(event.target.value))}>{[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{value} star{value === 1 ? "" : "s"}</option>)}</select></label><label className="mt-4 block"><span className="label">Comment (optional)</span><textarea className="field min-h-24" maxLength={1000} value={reviewText} onChange={(event) => setReviewText(event.target.value)}/></label><Button className="mt-5" disabled={busy} type="submit">Publish demo review</Button></form>}

    {booking.status === "COMPLETED" && <form className="card border-amber-200" onSubmit={dispute}><div className="flex items-center gap-3"><ShieldAlert className="text-amber-700"/><h2 className="text-xl font-black">Report a completion issue</h2></div><label className="mt-4 block"><span className="label">Reason</span><textarea className="field min-h-24" minLength={10} maxLength={1000} required value={disputeReason} onChange={(event) => setDisputeReason(event.target.value)}/></label><Button className="mt-5 bg-slate-700" disabled={busy} type="submit">Open demo dispute</Button></form>}
    {message && <p className="card border-amber-200 text-sm font-semibold" role="status">{message}</p>}
  </div>;
}
