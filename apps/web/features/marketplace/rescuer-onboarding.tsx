"use client";

import {FormEvent, useEffect, useRef, useState} from "react";
import {FileLock2, LocateFixed} from "lucide-react";
import {Button} from "@/components/ui/button";
import {EMPTY_DIRECTORY_LOCATION, LocationSelector, type DirectoryLocation} from "@/features/marketplace/location-selector";
import {api, ApiError} from "@/lib/api";
import type {LocationItem, MarketplacePage} from "@/lib/marketplace";

type Application = {id: string; verification_status: string};

export function RescuerOnboarding() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [location, setLocation] = useState<DirectoryLocation>(EMPTY_DIRECTORY_LOCATION);
  const [displayName, setDisplayName] = useState("");
  const [organization, setOrganization] = useState("");
  const [experience, setExperience] = useState(0);
  const [languages, setLanguages] = useState("");
  const [training, setTraining] = useState("");
  const [reference, setReference] = useState("");
  const [authority, setAuthority] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [coverage, setCoverage] = useState("");
  const [mandals, setMandals] = useState<LocationItem[]>([]);
  const [travelMandals, setTravelMandals] = useState<string[]>([]);
  const [radius, setRadius] = useState(25);
  const [latitude, setLatitude] = useState<number | undefined>();
  const [longitude, setLongitude] = useState<number | undefined>();
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!location.district_code) {
      setMandals([]);
      return;
    }
    api<MarketplacePage<LocationItem>>(
      `/api/v1/locations/subdistricts?district_code=${encodeURIComponent(location.district_code)}&limit=100`,
    )
      .then((result) => setMandals(result.items))
      .catch(() => setMandals([]));
  }, [location.district_code]);

  function toggleTravelMandal(code: string) {
    setTravelMandals((current) =>
      current.includes(code) ? current.filter((item) => item !== code) : [...current, code],
    );
  }

  function locate() {
    if (!navigator.geolocation) return setError("GPS unavailable. Coordinates are optional for onboarding.");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(Number(position.coords.latitude.toFixed(6)));
        setLongitude(Number(position.coords.longitude.toFixed(6)));
        setError("");
      },
      () => setError("Location permission was denied. You can still submit without coordinates."),
      {enableHighAccuracy: true, timeout: 12000},
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const application = await api<Application>("/api/v1/rescuers/onboarding", {
        method: "POST",
        body: JSON.stringify({
          public_display_name: displayName,
          ...location,
          subdistrict_code: location.subdistrict_code || undefined,
          village_code: location.village_code || undefined,
          organization_name: organization,
          years_experience: experience,
          languages: languages.split(",").map((item) => item.trim()).filter(Boolean),
          training_details: training,
          authorization_reference: reference,
          issuing_authority: authority,
          authorization_issue_date: issueDate,
          authorization_expiry: expiryDate,
          service_area_description: coverage,
          service_radius_km: radius,
          coverage_subdistrict_codes: travelMandals,
          latitude,
          longitude,
          operating_hours: {},
          acknowledgement: acknowledged,
        }),
      });
      const file = fileRef.current?.files?.[0];
      if (file) {
        const body = new FormData();
        body.append("file", file);
        await api("/api/v1/rescuers/onboarding/documents", {method: "POST", body});
      }
      setSuccess(`Application ${application.id} is ${application.verification_status}. No role or authorization was granted automatically.`);
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401 ? "Sign in with a citizen account before applying." : reason instanceof Error ? reason.message : "Application could not be submitted.");
    } finally {
      setBusy(false);
    }
  }

  return <form className="space-y-7" onSubmit={submit}>
    <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm leading-6 text-red-950"><strong>Application only.</strong> Public signup never grants VERIFIED or RESCUER status. An administrator must separately review private evidence, organization affiliation, issuing authority and expiry. Application verification does not replace legal wildlife authorization.</div>
    <section className="card space-y-5"><div><p className="eyebrow">Identity and affiliation</p><h2 className="mt-2 text-xl font-black">Public profile information</h2></div><div className="grid gap-4 md:grid-cols-2"><label><span className="label">Approved public display name</span><input className="field" required minLength={2} maxLength={120} value={displayName} onChange={(event) => setDisplayName(event.target.value)}/></label><label><span className="label">Organization affiliation</span><input className="field" required minLength={2} maxLength={180} value={organization} onChange={(event) => setOrganization(event.target.value)}/></label><label><span className="label">Relevant experience (years)</span><input className="field" required type="number" min={0} max={80} value={experience} onChange={(event) => setExperience(Number(event.target.value))}/></label><label><span className="label">Languages spoken</span><input className="field" required placeholder="Telugu, English" value={languages} onChange={(event) => setLanguages(event.target.value)}/></label></div><label><span className="label">Training details</span><textarea className="field min-h-28" required minLength={10} maxLength={2000} value={training} onChange={(event) => setTraining(event.target.value)}/></label></section>
    <section className="card space-y-5"><div><p className="eyebrow">Official location hierarchy</p><h2 className="mt-2 text-xl font-black">Primary demo service area</h2></div><LocationSelector value={location} onChange={setLocation} required/><label><span className="label">Coverage description</span><textarea className="field min-h-24" required minLength={5} maxLength={500} value={coverage} onChange={(event) => setCoverage(event.target.value)}/></label>{mandals.length > 0 && <div><p className="label">Other mandals you will travel to</p><p className="mb-3 text-xs text-slate-500">Optional. Tick the mandals (besides your own) you are willing to travel to. Customers there will see a &quot;Serves your mandal&quot; badge.</p><div className="grid max-h-56 gap-2 overflow-y-auto rounded-xl border p-4 sm:grid-cols-2">{mandals.map((item) => <label className="flex items-center gap-3 text-sm" key={item.lgd_code}><input className="h-4 w-4" type="checkbox" checked={travelMandals.includes(item.lgd_code)} onChange={() => toggleTravelMandal(item.lgd_code)}/><span>{item.name}</span></label>)}</div>{travelMandals.length > 0 && <p className="mt-2 text-xs font-semibold text-forest">{travelMandals.length} extra mandal(s) selected</p>}</div>}
    <div className="grid gap-4 md:grid-cols-3"><label><span className="label">Maximum demo radius (km)</span><input className="field" type="number" min={1} max={100} value={radius} onChange={(event) => setRadius(Number(event.target.value))}/></label><label><span className="label">Private base latitude (optional)</span><input className="field" type="number" min={-90} max={90} step="any" value={latitude ?? ""} onChange={(event) => setLatitude(event.target.value ? Number(event.target.value) : undefined)}/></label><label><span className="label">Private base longitude (optional)</span><input className="field" type="number" min={-180} max={180} step="any" value={longitude ?? ""} onChange={(event) => setLongitude(event.target.value ? Number(event.target.value) : undefined)}/></label></div><Button type="button" className="border border-forest bg-white text-forest" onClick={locate}><LocateFixed size={18}/>Capture optional private base location</Button><p className="text-xs text-slate-500">Exact rescuer coordinates are used only for protected matching and are never returned by public profile APIs.</p></section>
    <section className="card space-y-5"><div><p className="eyebrow">Private authorization evidence</p><h2 className="mt-2 text-xl font-black">Administrator review details</h2></div><div className="grid gap-4 md:grid-cols-2"><label><span className="label">Authorization reference</span><input className="field" required minLength={3} maxLength={160} value={reference} onChange={(event) => setReference(event.target.value)}/></label><label><span className="label">Issuing authority</span><input className="field" required minLength={3} maxLength={180} value={authority} onChange={(event) => setAuthority(event.target.value)}/></label><label><span className="label">Issue date</span><input className="field" required type="date" value={issueDate} onChange={(event) => setIssueDate(event.target.value)}/></label><label><span className="label">Expiry date</span><input className="field" required type="date" value={expiryDate} onChange={(event) => setExpiryDate(event.target.value)}/></label></div><label className="block rounded-xl border border-dashed border-slate-400 p-5"><span className="flex items-center gap-2 font-bold"><FileLock2 size={18}/>Private evidence file</span><span className="mt-2 block text-xs leading-5 text-slate-500">Optional at form submission but required before approval. JPEG, PNG, WebP or PDF; maximum 10 MB. Stored privately and never published.</span><input ref={fileRef} className="mt-4 block w-full text-sm" type="file" accept="application/pdf,image/jpeg,image/png,image/webp"/></label><label className="flex items-start gap-3"><input className="mt-1 h-5 w-5" required type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)}/><span className="text-sm leading-6">I understand this is a demo application, verification is administrator-controlled, and application status does not replace state-specific legal wildlife authorization.</span></label></section>
    {error && <p className="rounded-xl bg-red-50 p-4 text-sm font-semibold text-danger" role="alert">{error}</p>}
    {success && <p className="rounded-xl bg-green-50 p-4 text-sm font-semibold text-forest" role="status">{success}</p>}
    <Button type="submit" disabled={busy}>{busy ? "Submitting securely…" : "Submit demo rescuer application"}</Button>
  </form>;
}
