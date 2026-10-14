"use client";

import {useRouter} from "next/navigation";
import {FormEvent, useEffect, useRef, useState} from "react";
import {AlertTriangle, LocateFixed} from "lucide-react";
import {LocationMap} from "@/components/location-map";
import {Button} from "@/components/ui/button";
import {EMPTY_DIRECTORY_LOCATION, LocationSelector, type DirectoryLocation} from "@/features/marketplace/location-selector";
import {api, ApiError} from "@/lib/api";
import type {Booking, PublicRescuer} from "@/lib/marketplace";

export function BookingForm({rescuerId}: {rescuerId: string}) {
  const router = useRouter();
  const idempotencyKey = useRef("");
  const [rescuer, setRescuer] = useState<PublicRescuer | null>(null);
  const [location, setLocation] = useState<DirectoryLocation>(EMPTY_DIRECTORY_LOCATION);
  const [latitude, setLatitude] = useState<number | undefined>();
  const [longitude, setLongitude] = useState<number | undefined>();
  const [accuracy, setAccuracy] = useState<number | undefined>();
  const [manualAddress, setManualAddress] = useState("");
  const [landmark, setLandmark] = useState("");
  const [notes, setNotes] = useState("");
  const [injury, setInjury] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<PublicRescuer>(`/api/v1/rescuers/${encodeURIComponent(rescuerId)}`)
      .then(setRescuer)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load the selected profile."));
  }, [rescuerId]);

  function locate() {
    if (!navigator.geolocation) {
      setMessage("GPS is unavailable. Manual address and directory selection remain usable.");
      return;
    }
    setMessage("Requesting location permission…");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(Number(position.coords.latitude.toFixed(6)));
        setLongitude(Number(position.coords.longitude.toFixed(6)));
        setAccuracy(position.coords.accuracy);
        setMessage(`Captured with ±${Math.round(position.coords.accuracy)} m accuracy. Review the marker before continuing.`);
      },
      () => setMessage("Location permission was denied or timed out. Enter a manual address and select the LGD area."),
      {enableHighAccuracy: true, timeout: 12000, maximumAge: 30000},
    );
  }

  function review(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!location.state_code || !location.district_code) {
      setError("Select an imported LGD state and district.");
      return;
    }
    if (!manualAddress.trim() && (!Number.isFinite(latitude) || !Number.isFinite(longitude))) {
      setError("Enter a manual address or confirm coordinates.");
      return;
    }
    if (notes.trim().length < 10) {
      setError("Describe the situation in at least 10 characters.");
      return;
    }
    if (!confirmed) {
      setError("Confirm the demo and safety acknowledgement.");
      return;
    }
    setReviewing(true);
  }

  async function submit() {
    if (busy) return;
    if (!idempotencyKey.current) {
      idempotencyKey.current = crypto.randomUUID();
    }
    setBusy(true);
    setError("");
    try {
      const booking = await api<Booking>("/api/v1/bookings", {
        method: "POST",
        headers: {"Idempotency-Key": idempotencyKey.current},
        body: JSON.stringify({
          rescuer_id: rescuerId,
          state_code: location.state_code,
          district_code: location.district_code || undefined,
          subdistrict_code: location.subdistrict_code || undefined,
          village_code: location.village_code || undefined,
          manual_address: manualAddress.trim() || undefined,
          landmark: landmark.trim() || undefined,
          latitude,
          longitude,
          location_accuracy: accuracy,
          customer_notes: injury ? `[Injury reported — call 112 guidance shown] ${notes.trim()}` : notes.trim(),
          confirm_demo_and_safety: true,
        }),
      });
      router.push(`/bookings/${booking.id}?created=1`);
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401
        ? "Sign in as a citizen before submitting this demo request."
        : reason instanceof Error ? reason.message : "The demo request could not be created.");
    } finally {
      setBusy(false);
    }
  }

  if (!rescuer && !error) return <div className="card" role="status">Loading selected demo profile…</div>;
  if (!rescuer) return <div className="card border-red-200" role="alert">{error}</div>;

  if (reviewing) return <div className="space-y-6"><div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">DEMO BOOKING — this does not dispatch a real rescuer or replace emergency services.</div><section className="card"><p className="eyebrow">Final review</p><h2 className="mt-2 text-2xl font-black">Request to {rescuer.display_name}</h2><dl className="mt-6 grid gap-5 sm:grid-cols-2"><div><dt className="text-xs font-bold uppercase text-slate-500">Organization</dt><dd className="mt-1">{rescuer.organization}</dd></div><div><dt className="text-xs font-bold uppercase text-slate-500">Demo availability</dt><dd className="mt-1">{rescuer.availability}</dd></div><div><dt className="text-xs font-bold uppercase text-slate-500">LGD codes</dt><dd className="mt-1">{location.state_code} / {location.district_code}{location.village_code ? ` / ${location.village_code}` : ""}</dd></div><div><dt className="text-xs font-bold uppercase text-slate-500">Coordinates</dt><dd className="mt-1">{latitude === undefined ? "Manual location only" : `${latitude}, ${longitude}`}</dd></div><div className="sm:col-span-2"><dt className="text-xs font-bold uppercase text-slate-500">Location description</dt><dd className="mt-1">{manualAddress || "Coordinate location confirmed"}{landmark ? ` · ${landmark}` : ""}</dd></div><div className="sm:col-span-2"><dt className="text-xs font-bold uppercase text-slate-500">Situation</dt><dd className="mt-1 leading-6">{notes}</dd></div></dl><div className="mt-7 rounded-xl bg-mist p-4 text-sm"><strong>Charges and payments are disabled.</strong> The displayed 10% commission concept is illustrative only; this booking stores a ₹0.00 financial snapshot and collects nothing.</div><div className="mt-7 flex flex-wrap gap-3"><Button type="button" className="border border-slate-300 bg-white text-slate-700" onClick={() => setReviewing(false)}>Edit details</Button><Button type="button" disabled={busy} onClick={() => void submit()}>{busy ? "Submitting once…" : "Submit simulated request"}</Button></div>{error && <p className="mt-4 text-sm font-semibold text-danger" role="alert">{error}</p>}</section></div>;

  return <form className="space-y-7" onSubmit={review}>
    <div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">Demo Platform — Not an Active Emergency Rescue Service. No live dispatch or payment will occur.</div>
    {injury && <div className="rounded-2xl border-2 border-danger bg-red-50 p-6" role="alert"><div className="flex items-center gap-3"><AlertTriangle className="text-danger"/><h2 className="text-xl font-black text-danger">Call 112 and seek immediate medical care now</h2></div><p className="mt-3 text-sm leading-6 text-red-950">Submitting this form is not a substitute for emergency medical assistance. Do not wait for a response from this demo platform.</p></div>}
    <section className="card"><p className="eyebrow">Selected simulated profile</p><h2 className="mt-2 text-2xl font-black">{rescuer.display_name}</h2><p className="mt-2 text-sm text-slate-600">{rescuer.organization} · {rescuer.service_area}</p></section>
    <section className="card space-y-5"><div><p className="eyebrow">Location</p><h2 className="mt-2 text-xl font-black">Confirm where assistance would be requested</h2></div><LocationSelector value={location} onChange={setLocation} required/><div className="grid gap-4 md:grid-cols-2"><label><span className="label">Manual address description</span><textarea className="field min-h-28" maxLength={500} value={manualAddress} onChange={(event) => setManualAddress(event.target.value)} placeholder="Building, street or access directions. Do not approach the snake."/></label><label><span className="label">Landmark (optional)</span><textarea className="field min-h-28" maxLength={200} value={landmark} onChange={(event) => setLandmark(event.target.value)}/></label></div><div className="grid gap-4 md:grid-cols-3"><label><span className="label">Latitude</span><input className="field" type="number" step="any" min={-90} max={90} value={latitude ?? ""} onChange={(event) => setLatitude(event.target.value ? Number(event.target.value) : undefined)}/></label><label><span className="label">Longitude</span><input className="field" type="number" step="any" min={-180} max={180} value={longitude ?? ""} onChange={(event) => setLongitude(event.target.value ? Number(event.target.value) : undefined)}/></label><div className="flex items-end"><Button className="w-full" type="button" onClick={locate}><LocateFixed size={18}/>Use current location</Button></div></div>{message && <p className="text-sm text-slate-600" role="status">{message}</p>}<LocationMap latitude={latitude} longitude={longitude} accuracy={accuracy} onChange={(lat, lng) => {setLatitude(lat); setLongitude(lng);}}/></section>
    <section className="card space-y-5"><label className="flex items-start gap-3 rounded-xl border p-4"><input className="mt-1 h-5 w-5" type="checkbox" checked={injury} onChange={(event) => setInjury(event.target.checked)}/><span><strong className="block">Is anyone bitten or injured?</strong><span className="mt-1 block text-sm text-slate-600">Selecting this immediately shows medical emergency guidance; it does not trigger dispatch.</span></span></label><label><span className="label">Incident details</span><textarea className="field min-h-36" required minLength={10} maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Describe what you can see from a safe distance. Never approach, handle or photograph the snake."/></label><label className="flex items-start gap-3"><input className="mt-1 h-5 w-5" type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)}/><span className="text-sm leading-6">I understand this creates a simulated booking only, does not contact a real rescuer, collects no payment, and is not a substitute for 112 or medical care.</span></label></section>
    {error && <p className="text-sm font-semibold text-danger" role="alert">{error}</p>}
    <Button type="submit">Review simulated request</Button>
  </form>;
}
