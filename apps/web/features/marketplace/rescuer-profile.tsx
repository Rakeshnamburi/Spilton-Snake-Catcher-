"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {BadgeIndianRupee, CalendarClock, Languages, ShieldAlert, Star} from "lucide-react";
import {api, ApiError} from "@/lib/api";
import {humanize, type PublicRescuer} from "@/lib/marketplace";

export function RescuerProfileView({id}: {id: string}) {
  const [rescuer, setRescuer] = useState<PublicRescuer | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<PublicRescuer>(`/api/v1/rescuers/${encodeURIComponent(id)}`)
      .then(setRescuer)
      .catch((reason) => setError(reason instanceof ApiError ? reason.message : "Unable to load this profile."));
  }, [id]);

  if (error) return <div className="card border-red-200" role="alert"><h2 className="text-xl font-black text-danger">Profile unavailable</h2><p className="mt-3 text-sm leading-6">{error}</p><Link className="mt-5 inline-block font-bold text-forest" href="/rescuers">Return to directory</Link></div>;
  if (!rescuer) return <div className="card" role="status">Loading protected demo profile…</div>;

  return <div className="space-y-7">
    <div className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-sm leading-6 text-amber-950"><strong>Fictional demo profile.</strong> Its verification, availability, history and metrics are simulated test data and are not claims of real wildlife authorization or emergency readiness.</div>
    <section className="card overflow-hidden p-0"><div className="bg-gradient-to-br from-forest to-emerald p-8 text-white"><span className="rounded-full bg-white/15 px-3 py-1 text-xs font-black">SIMULATED PROFILE</span><h1 className="mt-5 text-4xl font-black">{rescuer.display_name}</h1><p className="mt-2 text-green-50">{rescuer.organization}</p></div><div className="grid gap-8 p-8 lg:grid-cols-[1fr_.65fr]"><div><h2 className="text-xl font-black">Service profile</h2><dl className="mt-5 grid gap-5 sm:grid-cols-2"><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Verification</dt><dd className="mt-2 flex items-center gap-2 font-bold text-forest"><ShieldAlert size={18}/>Simulated {humanize(rescuer.verification_status)}</dd></div><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Availability</dt><dd className="mt-2 font-bold">{humanize(rescuer.availability)} — demo only</dd></div><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Experience supplied</dt><dd className="mt-2">{rescuer.years_experience} year{rescuer.years_experience === 1 ? "" : "s"}</dd></div><div><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Authorization expiry</dt><dd className="mt-2 flex items-center gap-2"><CalendarClock size={18}/>{rescuer.authorization_expiry ? new Date(`${rescuer.authorization_expiry}T00:00:00`).toLocaleDateString() : "Not published"}</dd></div><div className="sm:col-span-2"><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Approved demo service area</dt><dd className="mt-2 leading-6">{rescuer.service_area}</dd></div><div className="sm:col-span-2"><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Languages</dt><dd className="mt-2 flex items-center gap-2"><Languages size={18}/>{rescuer.languages.join(", ")}</dd></div></dl></div><aside className="rounded-2xl bg-mist p-6"><h2 className="font-black">Marketplace transparency</h2><div className="mt-5 space-y-4 text-sm"><p className="flex items-center gap-2"><Star size={18}/>{rescuer.review_count ? `${rescuer.average_rating} demo rating from ${rescuer.review_count} simulated reviews` : "No demo reviews yet"}</p><p>{rescuer.completed_service_count} simulated completed services; not real performance history.</p><p className="flex items-center gap-2"><BadgeIndianRupee size={18}/><strong>Charges disabled.</strong> No payment is collected.</p></div>{rescuer.availability === "AVAILABLE" ? <Link className="mt-6 block rounded-xl bg-forest px-5 py-3 text-center text-sm font-bold text-white" href={`/book/${rescuer.id}`}>Request simulated assistance</Link> : <p className="mt-6 rounded-xl bg-slate-200 p-4 text-center text-sm font-bold text-slate-600">Not accepting demo requests</p>}</aside></div></section>
    <p className="text-sm leading-6 text-slate-600">Verification in this prototype is an internal application status and does not replace wildlife authorization. Private identity documents, personal addresses and exact rescuer coordinates are never shown here.</p>
  </div>;
}
