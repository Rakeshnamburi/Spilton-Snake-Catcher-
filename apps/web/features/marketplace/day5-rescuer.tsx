"use client";

import {FormEvent, useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";
import type {Booking} from "@/lib/marketplace";

export function RescuerCompletionPanel({
  booking,
  onRefresh,
}: {
  booking: Booking;
  onRefresh: () => Promise<void>;
}) {
  const [outcomes, setOutcomes] = useState<Array<{code: string; label: string}>>([]);
  const [outcome, setOutcome] = useState("AUTHORIZED_RESCUE_COMPLETED");
  const [observations, setObservations] = useState("");
  const [actionSummary, setActionSummary] = useState("");
  const [speciesText, setSpeciesText] = useState("");
  const [evidence, setEvidence] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Array<{code: string; label: string}>>("/api/v1/rescue-outcomes")
      .then(setOutcomes)
      .catch(() => setMessage("Outcome directory unavailable."));
  }, []);

  async function startWork() {
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + booking.id + "/rescue/start", {method: "POST"});
      setMessage("Simulated rescue record started.");
      await onRefresh();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Could not start.");
    } finally {
      setBusy(false);
    }
  }

  async function complete(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      if (evidence) {
        const form = new FormData();
        form.set("evidence_type", "OUTCOME");
        form.set("file", evidence);
        await api("/api/v1/bookings/" + booking.id + "/rescue/evidence", {
          method: "POST",
          body: form,
        });
      }
      await api("/api/v1/bookings/" + booking.id + "/complete", {
        method: "POST",
        headers: {"Idempotency-Key": "web-completion-" + crypto.randomUUID()},
        body: JSON.stringify({
          outcome_code: outcome,
          observations,
          authorized_action_summary: actionSummary,
          species_text: speciesText || null,
          confirm_demo: true,
        }),
      });
      setMessage("Demo completion report saved; tracking stopped.");
      await onRefresh();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Completion failed.");
    } finally {
      setBusy(false);
    }
  }

  if (booking.status === "ARRIVED") {
    return <section className="card">
      <h2 className="text-xl font-black">Begin the simulated rescue record</h2>
      <p className="mt-2 text-sm text-slate-600">This changes the demo booking to in progress. It does not authorize wildlife handling.</p>
      <Button className="mt-5" disabled={busy} onClick={() => void startWork()}>Start demo work record</Button>
      {message && <p className="mt-4 text-sm font-semibold">{message}</p>}
    </section>;
  }
  if (booking.status !== "IN_PROGRESS") return null;
  return <form className="card" onSubmit={complete}>
    <h2 className="text-xl font-black">Complete simulated rescue record</h2>
    <p className="mt-2 text-sm text-danger">Use factual, non-medical notes. Species text remains unverified and is never a safety decision.</p>
    <label className="mt-5 block"><span className="label">Outcome</span><select className="field" value={outcome} onChange={(event) => setOutcome(event.target.value)}>{outcomes.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>
    <label className="mt-4 block"><span className="label">Observations</span><textarea className="field min-h-28" minLength={5} maxLength={4000} required value={observations} onChange={(event) => setObservations(event.target.value)}/></label>
    <label className="mt-4 block"><span className="label">Authorized action summary</span><textarea className="field min-h-28" minLength={5} maxLength={4000} required value={actionSummary} onChange={(event) => setActionSummary(event.target.value)}/></label>
    <label className="mt-4 block"><span className="label">Species note (optional, unverified)</span><input className="field" maxLength={160} value={speciesText} onChange={(event) => setSpeciesText(event.target.value)}/></label>
    <label className="mt-4 block"><span className="label">Optional private image (JPEG, PNG or WebP; max 5 MB)</span><input className="field" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setEvidence(event.target.files?.[0] ?? null)}/><span className="mt-2 block text-xs text-slate-500">Never approach a snake to take a photo. Video stays disabled until safe processing is configured.</span></label>
    <Button className="mt-6" disabled={busy} type="submit">{busy ? "Saving…" : "Submit demo completion"}</Button>
    {message && <p className="mt-4 text-sm font-semibold" role="status">{message}</p>}
  </form>;
}
