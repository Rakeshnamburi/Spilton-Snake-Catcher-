"use client";

import Link from "next/link";
import {FormEvent, useState} from "react";
import {Clock3, Languages, List, LocateFixed, Map as MapIcon, ShieldCheck} from "lucide-react";
import {LocationMap} from "@/components/location-map";
import {Button} from "@/components/ui/button";
import {LocationSelector, EMPTY_DIRECTORY_LOCATION, type DirectoryLocation} from "@/features/marketplace/location-selector";
import {api, ApiError} from "@/lib/api";
import {humanize, type MarketplacePage, type PublicRescuer} from "@/lib/marketplace";
import {estimateFare, formatInr} from "@/lib/pricing";

export function RescuerDirectory() {
  const [location, setLocation] = useState<DirectoryLocation>(EMPTY_DIRECTORY_LOCATION);
  const [latitude, setLatitude] = useState<number | undefined>();
  const [longitude, setLongitude] = useState<number | undefined>();
  const [accuracy, setAccuracy] = useState<number | undefined>();
  const [radius, setRadius] = useState(25);
  const [experience, setExperience] = useState(0);
  const [language, setLanguage] = useState("");
  const [mode, setMode] = useState<"list" | "map">("list");
  const [result, setResult] = useState<MarketplacePage<PublicRescuer> | null>(null);
  const [loading, setLoading] = useState(false);
  const [gpsState, setGpsState] = useState("");
  const [error, setError] = useState("");

  function locate() {
    if (!navigator.geolocation) {
      setGpsState("Location is unavailable in this browser. Use directory or manual coordinates.");
      return;
    }
    setGpsState("Requesting foreground location permission…");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(Number(position.coords.latitude.toFixed(6)));
        setLongitude(Number(position.coords.longitude.toFixed(6)));
        setAccuracy(position.coords.accuracy);
        setGpsState(`Location captured with ±${Math.round(position.coords.accuracy)} m accuracy. Please review it.`);
      },
      (reason) => setGpsState(reason.code === reason.PERMISSION_DENIED
        ? "Permission was denied. Directory and manual coordinate search remain available."
        : "Location could not be captured. Try again or use manual location."),
      {enableHighAccuracy: true, timeout: 12000, maximumAge: 30000},
    );
  }

  async function search(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const query = new URLSearchParams({radius_km: String(radius), min_experience: String(experience)});
    if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
      query.set("latitude", String(latitude));
      query.set("longitude", String(longitude));
    }
    if (location.state_code) query.set("state_code", location.state_code);
    if (location.district_code) query.set("district_code", location.district_code);
    if (location.subdistrict_code) query.set("subdistrict_code", location.subdistrict_code);
    if (language.trim()) query.set("language", language.trim());
    try {
      setResult(await api<MarketplacePage<PublicRescuer>>(`/api/v1/rescuers/nearby?${query}`));
    } catch (reason) {
      setResult(null);
      setError(reason instanceof ApiError ? reason.message : "Unable to search the protected demo directory.");
    } finally {
      setLoading(false);
    }
  }

  return <div className="space-y-8">
    <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm leading-6 text-red-950"><strong>Simulated directory only.</strong> No profile shown here represents live emergency availability, and no request dispatches a real rescuer. For a suspected snakebite, call <strong>112</strong> and seek immediate medical care.</div>
    <form className="card space-y-6" onSubmit={search}>
      <div><p className="eyebrow">Confirm your search area</p><h2 className="mt-2 text-2xl font-black">Find eligible fictional demo profiles</h2></div>
      <LocationSelector value={location} onChange={setLocation}/>
      <div className="grid gap-4 md:grid-cols-3">
        <label><span className="label">Latitude (optional)</span><input className="field" type="number" min={-90} max={90} step="any" value={latitude ?? ""} onChange={(event) => setLatitude(event.target.value ? Number(event.target.value) : undefined)}/></label>
        <label><span className="label">Longitude (optional)</span><input className="field" type="number" min={-180} max={180} step="any" value={longitude ?? ""} onChange={(event) => setLongitude(event.target.value ? Number(event.target.value) : undefined)}/></label>
        <div className="flex items-end"><Button type="button" className="w-full" onClick={locate}><LocateFixed size={18}/>Use current location</Button></div>
      </div>
      {gpsState && <p className="text-sm text-slate-600" role="status">{gpsState}</p>}
      <div className="grid gap-4 md:grid-cols-3">
        <label><span className="label">Maximum distance</span><select className="field" value={radius} onChange={(event) => setRadius(Number(event.target.value))}><option value={10}>10 km</option><option value={25}>25 km</option><option value={50}>50 km</option><option value={100}>100 km</option></select></label>
        <label><span className="label">Minimum experience</span><select className="field" value={experience} onChange={(event) => setExperience(Number(event.target.value))}><option value={0}>Any</option><option value={2}>2+ years</option><option value={5}>5+ years</option><option value={10}>10+ years</option></select></label>
        <label><span className="label">Language</span><input className="field" maxLength={60} placeholder="e.g. Telugu" value={language} onChange={(event) => setLanguage(event.target.value)}/></label>
      </div>
      <Button type="submit" disabled={loading || (!location.state_code && !Number.isFinite(latitude))}>{loading ? "Searching…" : "Search demo directory"}</Button>
      {error && <p className="text-sm font-semibold text-danger" role="alert">{error}</p>}
    </form>

    {result && <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Protected discovery</p><h2 className="mt-2 text-2xl font-black">{result.total} eligible demo profile{result.total === 1 ? "" : "s"}</h2></div><div className="flex rounded-xl border bg-white p-1"><button className={`rounded-lg px-4 py-2 text-sm font-bold ${mode === "list" ? "bg-forest text-white" : "text-slate-600"}`} onClick={() => setMode("list")} type="button"><List className="mr-2 inline" size={16}/>List</button><button className={`rounded-lg px-4 py-2 text-sm font-bold ${mode === "map" ? "bg-forest text-white" : "text-slate-600"}`} onClick={() => setMode("map")} type="button"><MapIcon className="mr-2 inline" size={16}/>Map</button></div></div>
      {mode === "map" && <div className="space-y-3"><LocationMap latitude={latitude} longitude={longitude} accuracy={accuracy} onChange={(lat, lng) => {setLatitude(lat); setLongitude(lng);}}/><p className="text-xs leading-5 text-slate-500">This preview shows your selected search point only. Rescuer home coordinates are private and are never placed on a public map.</p></div>}
      {!result.items.length ? <div className="card text-center"><h3 className="text-xl font-black">No eligible demo rescuer is available</h3><p className="mt-3 text-sm leading-6 text-slate-600">No profile satisfied verification, organization, expiry, availability, coverage, and distance checks. This platform is not a dispatch service.</p><Link className="mt-5 inline-flex rounded-xl bg-danger px-5 py-3 text-sm font-bold text-white" href="/emergency">View verified public emergency contacts</Link></div> : <div className="grid gap-5 lg:grid-cols-2">{result.items.map((rescuer) => <article className="card" key={rescuer.id}><div className="flex items-start justify-between gap-4"><div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-900">FICTIONAL DEMO PROFILE</span>{rescuer.coverage_scope && rescuer.coverage_scope !== "OTHER" && <span className="ml-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-900">{rescuer.coverage_scope === "MANDAL" ? "Serves your mandal" : rescuer.coverage_scope === "DISTRICT" ? "Same district" : "Same state"}</span>}<h3 className="mt-4 text-2xl font-black text-forest">{rescuer.display_name}</h3><p className="mt-1 text-sm text-slate-600">{rescuer.organization}</p></div><ShieldCheck className="text-emerald" aria-label="Simulated verification recorded"/></div><dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-bold text-slate-500">Application status</dt><dd className="mt-1 font-bold text-forest">Simulated {humanize(rescuer.verification_status)}</dd></div><div><dt className="font-bold text-slate-500">Distance</dt><dd className="mt-1">{rescuer.distance_km === null ? "Directory match" : `About ${rescuer.distance_km} km${rescuer.eta_minutes != null ? ` · about ${rescuer.eta_minutes} min` : ""}`}</dd></div><div><dt className="flex items-center gap-2 font-bold text-slate-500"><Clock3 size={15}/>Availability</dt><dd className="mt-1">{humanize(rescuer.availability)} (demo)</dd></div><div><dt className="flex items-center gap-2 font-bold text-slate-500"><Languages size={15}/>Languages</dt><dd className="mt-1">{rescuer.languages.join(", ")}</dd></div></dl><p className="mt-5 text-sm leading-6 text-slate-600">{rescuer.service_area}</p><p className="mt-4 rounded-xl bg-mist p-3 text-sm"><strong>Illustrative fare:</strong> {formatInr(estimateFare(rescuer.distance_km).total)}{rescuer.distance_km != null ? ` (base ${formatInr(estimateFare(rescuer.distance_km).baseFare)} + ~${rescuer.distance_km} km travel)` : " (base callout)"} — demo estimate, no real charge.</p><div className="mt-6 flex flex-wrap gap-3"><Link className="rounded-xl border border-forest px-4 py-3 text-sm font-bold text-forest" href={`/rescuers/${rescuer.id}`}>View profile</Link><Link className="rounded-xl bg-forest px-4 py-3 text-sm font-bold text-white" href={`/book/${rescuer.id}${rescuer.distance_km != null ? `?distance=${rescuer.distance_km}` : ""}`}>Request simulated assistance</Link></div></article>)}</div>}
    </section>}
  </div>;
}
