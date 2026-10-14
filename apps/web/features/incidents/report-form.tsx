"use client";

import Image from "next/image";
import Link from "next/link";
import {useEffect, useMemo, useRef, useState} from "react";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {Check, ChevronLeft, ChevronRight, FileImage, LocateFixed, MapPin, PhoneCall, TriangleAlert, X} from "lucide-react";
import {Button} from "@/components/ui/button";
import {LocationMap} from "@/components/location-map";
import {api, ApiError} from "@/lib/api";
import {useI18n, TranslationReviewNotice} from "@/lib/i18n";
import type {Incident, IncidentMedia} from "@/lib/incidents";
import {isCoordinateInState, REGIONS, TARGET_STATES, type RegionState} from "@/lib/regions";

const optionalNumber = z.preprocess((value) => value === "" || value === null ? undefined : value, z.coerce.number().optional());
const stateSchema = z.enum(
  ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu", "Kerala"],
  {errorMap: () => ({message: "Select a state."})},
);
const schema = z.object({
  state: stateSchema,
  district: z.string().min(2, "Select a district."),
  city: z.string().trim().min(2, "Enter the city or village."),
  landmark: z.string().trim().max(200).optional(),
  address_description: z.string().trim().max(500).optional(),
  sighting_at: z.string().min(1, "Enter the sighting date and time."),
  description: z.string().trim().min(10, "Add at least 10 characters.").max(2000),
  injury: z.enum(["YES", "NO"]),
  snake_visible: z.enum(["YES", "NO"]),
  immediate_danger: z.enum(["YES", "NO"]),
  latitude: optionalNumber.pipe(z.number().min(-90).max(90).optional()),
  longitude: optionalNumber.pipe(z.number().min(-180).max(180).optional()),
  location_accuracy: optionalNumber.pipe(z.number().min(0).max(10000).optional()),
  location_confirmed: z.boolean().refine(Boolean, "Review and confirm the location."),
  reporter_name: z.string().trim().min(2, "Enter the reporter name.").max(120),
  contact_phone: z.string().regex(/^\+?[0-9]{10,15}$/, "Enter 10–15 digits, optionally beginning with +."),
  reporter_email: z.union([z.literal(""), z.string().email("Enter a valid email address.")]).optional(),
  consent: z.boolean().refine(Boolean, "Consent is required."),
}).superRefine((values, context) => {
  if (!REGIONS[values.state].includes(values.district as never)) context.addIssue({code: z.ZodIssueCode.custom, path: ["district"], message: "Select a district in the chosen state."});
  const hasLatitude = values.latitude !== undefined;
  const hasLongitude = values.longitude !== undefined;
  if (hasLatitude !== hasLongitude) context.addIssue({code: z.ZodIssueCode.custom, path: [hasLatitude ? "longitude" : "latitude"], message: "Enter both latitude and longitude."});
  if (hasLatitude && hasLongitude && !isCoordinateInState(values.state, values.latitude as number, values.longitude as number)) context.addIssue({code: z.ZodIssueCode.custom, path: ["latitude"], message: "Coordinates appear outside the selected state. Check both fields."});
  if (new Date(values.sighting_at).getTime() > Date.now() + 5 * 60 * 1000) context.addIssue({code: z.ZodIssueCode.custom, path: ["sighting_at"], message: "Sighting time cannot be in the future."});
});

type Values = z.input<typeof schema>;
type GpsState = "idle" | "loading" | "success" | "denied" | "timeout" | "unavailable" | "error";
type SelectedImage = {file: File; preview: string};
const MAX_IMAGES = 3;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

function localDateTime() {
  const value = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000);
  return value.toISOString().slice(0, 16);
}

async function hasValidImageSignature(file: File) {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const jpeg = bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  const png = bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47 && bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a;
  const webp = String.fromCharCode(...bytes.slice(0, 4)) === "RIFF" && String.fromCharCode(...bytes.slice(8, 12)) === "WEBP";
  return file.type === "image/jpeg" ? jpeg : file.type === "image/png" ? png : file.type === "image/webp" ? webp : false;
}

const stepFields: Array<Array<keyof Values>> = [
  ["state", "district", "city", "sighting_at", "description"], ["injury", "snake_visible", "immediate_danger"],
  ["latitude", "longitude", "location_accuracy", "location_confirmed"], [],
  ["reporter_name", "contact_phone", "reporter_email", "consent"], [],
];

type Register = ReturnType<typeof useForm<Values>>["register"];
function Choice({label, name, value, register}: {label: string; name: "injury" | "snake_visible" | "immediate_danger"; value: "YES" | "NO"; register: Register}) {
  return <label className="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-slate-300 px-4 py-3 has-[:checked]:border-forest has-[:checked]:bg-green-50"><input type="radio" value={value} {...register(name)} className="h-4 w-4 accent-green-700"/><span className="font-semibold">{label}</span></label>;
}

export function ReportForm() {
  const {t} = useI18n();
  const [step, setStep] = useState(0);
  const [gpsState, setGpsState] = useState<GpsState>("idle");
  const [images, setImages] = useState<SelectedImage[]>([]);
  const [mediaError, setMediaError] = useState("");
  const [created, setCreated] = useState<Incident | null>(null);
  const [uploadWarning, setUploadWarning] = useState("");
  const submitLock = useRef(false);
  const idempotencyKey = useRef<string>(globalThis.crypto?.randomUUID?.() ?? `web-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const form = useForm<Values>({resolver: zodResolver(schema), mode: "onTouched", defaultValues: {
    district: "", city: "", landmark: "", address_description: "", sighting_at: localDateTime(), description: "",
    injury: "NO", snake_visible: "NO", immediate_danger: "NO", location_confirmed: false,
    reporter_name: "", contact_phone: "", reporter_email: "", consent: false,
  }});
  const {register, watch, setValue, setError, clearErrors, trigger, handleSubmit, formState: {errors, isSubmitting}} = form;
  const state = watch("state") as RegionState | undefined;
  const injury = watch("injury");
  const immediateDanger = watch("immediate_danger");
  const rawLatitude = watch("latitude");
  const rawLongitude = watch("longitude");
  const rawAccuracy = watch("location_accuracy");
  const latitude = rawLatitude === "" || rawLatitude === undefined ? undefined : Number(rawLatitude);
  const longitude = rawLongitude === "" || rawLongitude === undefined ? undefined : Number(rawLongitude);
  const accuracy = rawAccuracy === "" || rawAccuracy === undefined ? undefined : Number(rawAccuracy);
  const allValues = watch();
  const steps = useMemo(() => ["incident", "triage", "location", "media", "reporter", "review"].map((item) => t(`report.step.${item}`)), [t]);

  const imagesRef = useRef(images);
  imagesRef.current = images;
  useEffect(() => () => imagesRef.current.forEach((image) => URL.revokeObjectURL(image.preview)), []);

  async function next() {
    clearErrors("root");
    const valid = await trigger(stepFields[step], {shouldFocus: true});
    if (valid) { setStep((current) => Math.min(current + 1, steps.length - 1)); window.scrollTo({top: 0, behavior: "smooth"}); }
  }

  function locate() {
    clearErrors("root");
    if (!navigator.geolocation) { setGpsState("unavailable"); return; }
    setGpsState("loading");
    navigator.geolocation.getCurrentPosition((position) => {
      setValue("latitude", Number(position.coords.latitude.toFixed(6)), {shouldValidate: true});
      setValue("longitude", Number(position.coords.longitude.toFixed(6)), {shouldValidate: true});
      setValue("location_accuracy", Math.round(position.coords.accuracy), {shouldValidate: true});
      setValue("location_confirmed", false); setGpsState("success");
    }, (reason) => setGpsState(reason.code === reason.PERMISSION_DENIED ? "denied" : reason.code === reason.TIMEOUT ? "timeout" : reason.code === reason.POSITION_UNAVAILABLE ? "unavailable" : "error"), {enableHighAccuracy: true, timeout: 12_000, maximumAge: 30_000});
  }

  function updateMap(nextLatitude: number, nextLongitude: number) {
    setValue("latitude", nextLatitude, {shouldValidate: true}); setValue("longitude", nextLongitude, {shouldValidate: true});
    setValue("location_accuracy", undefined); setValue("location_confirmed", false);
  }

  async function chooseImages(event: React.ChangeEvent<HTMLInputElement>) {
    setMediaError("");
    const incoming = Array.from(event.target.files ?? []);
    if (images.length + incoming.length > MAX_IMAGES) { setMediaError(`You can attach no more than ${MAX_IMAGES} images.`); event.target.value = ""; return; }
    const accepted: SelectedImage[] = [];
    for (const file of incoming) {
      if (!ALLOWED_TYPES.includes(file.type)) { setMediaError(`${file.name}: only JPEG, PNG, and WebP are accepted.`); break; }
      if (file.size > MAX_IMAGE_BYTES) { setMediaError(`${file.name}: each image must be 5 MB or smaller.`); break; }
      if (!(await hasValidImageSignature(file))) { setMediaError(`${file.name}: the file contents do not match its image type.`); break; }
      accepted.push({file, preview: URL.createObjectURL(file)});
    }
    if (accepted.length === incoming.length) setImages((current) => [...current, ...accepted]);
    else accepted.forEach((image) => URL.revokeObjectURL(image.preview));
    event.target.value = "";
  }

  function removeImage(index: number) {
    setImages((current) => { URL.revokeObjectURL(current[index].preview); return current.filter((_, itemIndex) => itemIndex !== index); });
  }

  async function submit(values: Values) {
    if (submitLock.current) return;
    submitLock.current = true; setUploadWarning("");
    try {
      const parsed = schema.parse(values);
      const urgency = parsed.injury === "YES" ? "SNAKEBITE" : parsed.immediate_danger === "YES" ? "HIGH" : "STANDARD";
      const incident = await api<Incident>("/api/v1/incidents", {method: "POST", headers: {"Idempotency-Key": idempotencyKey.current}, body: JSON.stringify({
        reporter_name: parsed.reporter_name, contact_phone: parsed.contact_phone, reporter_email: parsed.reporter_email || undefined,
        state: parsed.state, district: parsed.district, city: parsed.city, landmark: parsed.landmark || undefined,
        address_description: parsed.address_description || undefined, sighting_at: new Date(parsed.sighting_at).toISOString(),
        latitude: parsed.latitude, longitude: parsed.longitude, location_accuracy: parsed.location_accuracy, description: parsed.description,
        injury_reported: parsed.injury === "YES", snake_visible: parsed.snake_visible === "YES", immediate_danger: parsed.immediate_danger === "YES", urgency, consent: parsed.consent,
      })});
      let uploaded = 0;
      for (const image of images) {
        const body = new FormData(); body.append("file", image.file, image.file.name);
        try { await api<IncidentMedia>(`/api/v1/incidents/${incident.id}/media`, {method: "POST", body}); uploaded += 1; }
        catch { setUploadWarning(`${uploaded} of ${images.length} images uploaded. The report is saved, but the remaining images were not uploaded.`); break; }
      }
      setCreated(incident);
    } catch (error) {
      submitLock.current = false;
      const message = error instanceof ApiError && error.status === 401 ? t("error.session") : error instanceof ApiError && error.status === 409 ? t("error.duplicate") : error instanceof Error ? error.message : t("error.network");
      setError("root", {message});
    }
  }

  if (created) return <section className="card mx-auto max-w-3xl border-green-300 bg-green-50" aria-live="polite"><div className="grid h-14 w-14 place-items-center rounded-full bg-forest text-white"><Check size={30}/></div><p className="mt-6 text-sm font-bold uppercase tracking-widest text-forest">{t("report.success")}</p><h2 className="mt-2 text-3xl font-black">{created.reference_code}</h2><p className="mt-3 text-slate-700">{t("report.confirmation")}</p>{uploadWarning && <p role="alert" className="mt-4 rounded-xl bg-amber-100 p-4 text-sm text-amber-900">{uploadWarning}</p>}<div className="mt-7 flex flex-wrap gap-3"><Link href={`/reports/${created.id}`} className="rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white">View private report</Link><Link href="/my-reports" className="rounded-xl border border-forest px-5 py-3 text-sm font-bold text-forest">My reports</Link></div></section>;

  const gpsMessage = gpsState === "loading" ? t("report.gpsLoading") : gpsState === "success" ? t("report.locationCaptured") : gpsState === "denied" ? t("report.gpsDenied") : gpsState === "timeout" ? t("report.gpsTimeout") : gpsState === "unavailable" || gpsState === "error" ? t("report.gpsUnavailable") : "";
  const latRegistration = register("latitude");
  const lngRegistration = register("longitude");

  return <form onSubmit={(event) => event.preventDefault()} className="mx-auto max-w-5xl" noValidate>
    <div className="mb-6 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-3 shadow-sm" aria-label={`Step ${step + 1} of ${steps.length}`}><ol className="flex min-w-[680px] items-center justify-between gap-2">{steps.map((label, index) => <li key={label} className={`flex flex-1 items-center gap-2 rounded-xl px-3 py-2 text-xs font-bold ${index === step ? "bg-forest text-white" : index < step ? "bg-green-50 text-forest" : "text-slate-500"}`} aria-current={index === step ? "step" : undefined}><span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full ${index === step ? "bg-white text-forest" : "bg-slate-100"}`}>{index < step ? <Check size={14}/> : index + 1}</span>{label}</li>)}</ol></div>
    <div className="card min-h-[440px]">
      <div className="mb-7 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-950"><TriangleAlert className="mr-2 inline" size={18}/><strong>{t("report.stayBack")}</strong><TranslationReviewNotice/></div>
      {step === 0 && <fieldset className="space-y-6"><legend className="text-2xl font-black">{t("report.step.incident")}</legend><p className="text-sm text-slate-600">{t("report.demo")}</p><div className="grid gap-5 md:grid-cols-2">
        <label><span className="label">{t("report.state")}</span><select className="field" value={state ?? ""} {...register("state", {onChange: () => setValue("district", "")})}><option value="" disabled>Select state</option>{TARGET_STATES.map((item) => <option key={item}>{item}</option>)}</select><small className="text-danger">{errors.state?.message}</small></label>
        <label><span className="label">{t("report.district")}</span><select className="field" disabled={!state} {...register("district")}><option value="">{state ? "Select district" : "Choose a state first"}</option>{state && REGIONS[state].map((item) => <option key={item}>{item}</option>)}</select><small className="text-danger">{errors.district?.message}</small></label>
        <label><span className="label">{t("report.city")}</span><input className="field" autoComplete="address-level2" {...register("city")}/><small className="text-danger">{errors.city?.message}</small></label>
        <label><span className="label">{t("report.landmark")}</span><input className="field" {...register("landmark")}/><small className="text-danger">{errors.landmark?.message}</small></label>
        <label className="md:col-span-2"><span className="label">{t("report.address")}</span><input className="field" autoComplete="street-address" {...register("address_description")}/><small className="text-danger">{errors.address_description?.message}</small></label>
        <label><span className="label">{t("report.sightedAt")}</span><input className="field" type="datetime-local" max={localDateTime()} {...register("sighting_at")}/><small className="text-danger">{errors.sighting_at?.message}</small></label>
      </div><label className="block"><span className="label">{t("report.description")}</span><textarea className="field min-h-32" placeholder="Describe where the snake was seen from a safe distance." {...register("description")}/><small className="text-danger">{errors.description?.message}</small></label></fieldset>}

      {step === 1 && <fieldset className="space-y-7"><legend className="text-2xl font-black">{t("report.step.triage")}</legend>
        <div><p className="label mb-3">{t("report.injury")}</p><div className="grid gap-3 sm:grid-cols-2"><Choice label={t("common.yes")} name="injury" value="YES" register={register}/><Choice label={t("common.no")} name="injury" value="NO" register={register}/></div></div>
        {injury === "YES" && <div className="rounded-2xl bg-danger p-6 text-white" role="alert"><div className="flex gap-3"><PhoneCall className="shrink-0"/><div><h3 className="text-xl font-black">Medical emergency</h3><p className="mt-2 leading-7">{t("report.medical")}</p><TranslationReviewNotice/><a className="mt-5 inline-flex min-h-12 items-center rounded-xl bg-white px-5 font-black text-danger" href="tel:112">Call 112 now</a></div></div></div>}
        <div><p className="label mb-3">{t("report.visible")}</p><div className="grid gap-3 sm:grid-cols-2"><Choice label={t("common.yes")} name="snake_visible" value="YES" register={register}/><Choice label={t("common.no")} name="snake_visible" value="NO" register={register}/></div></div>
        <div><p className="label mb-3">{t("report.danger")}</p><div className="grid gap-3 sm:grid-cols-2"><Choice label={t("common.yes")} name="immediate_danger" value="YES" register={register}/><Choice label={t("common.no")} name="immediate_danger" value="NO" register={register}/></div></div>
        {immediateDanger === "YES" && injury !== "YES" && <p className="rounded-xl bg-amber-100 p-4 text-sm font-semibold text-amber-950">Move everyone to a safe distance. If anyone is in immediate danger, call 112; this demo does not dispatch help.</p>}
      </fieldset>}

      {step === 2 && <fieldset className="space-y-6"><legend className="text-2xl font-black">{t("report.step.location")}</legend><p className="text-sm text-slate-600">{t("report.locationManual")}</p><Button type="button" onClick={locate} disabled={gpsState === "loading"} className="bg-slate-800"><LocateFixed size={18}/>{gpsState === "success" ? t("report.refreshGps") : t("report.gps")}</Button>{gpsMessage && <p role="status" className={`rounded-xl p-4 text-sm ${gpsState === "success" ? "bg-green-50 text-green-900" : "bg-amber-50 text-amber-950"}`}>{gpsMessage}</p>}
        <div className="grid gap-4 sm:grid-cols-3"><label><span className="label">{t("report.latitude")}</span><input className="field" type="number" inputMode="decimal" step="any" {...latRegistration} onChange={(event) => {latRegistration.onChange(event); setValue("location_confirmed", false);}}/><small className="text-danger">{errors.latitude?.message}</small></label><label><span className="label">{t("report.longitude")}</span><input className="field" type="number" inputMode="decimal" step="any" {...lngRegistration} onChange={(event) => {lngRegistration.onChange(event); setValue("location_confirmed", false);}}/><small className="text-danger">{errors.longitude?.message}</small></label><label><span className="label">{t("report.accuracy")} (m)</span><input className="field" type="number" inputMode="decimal" min="0" {...register("location_accuracy")}/><small className="text-danger">{errors.location_accuracy?.message}</small></label></div>
        <LocationMap latitude={latitude} longitude={longitude} accuracy={accuracy} onChange={updateMap}/><label className="flex items-start gap-3 rounded-xl border border-slate-300 p-4"><input className="mt-1 h-5 w-5 accent-green-700" type="checkbox" {...register("location_confirmed")}/><span className="text-sm font-semibold text-slate-700">{t("report.confirmLocation")}</span></label><small className="text-danger">{errors.location_confirmed?.message}</small>
      </fieldset>}

      {step === 3 && <fieldset className="space-y-6"><legend className="text-2xl font-black">{t("report.step.media")}</legend><div className="rounded-xl bg-amber-50 p-4 text-sm font-semibold text-amber-950">{t("report.photoSafety")}</div><label className="block rounded-2xl border-2 border-dashed border-slate-300 p-8 text-center hover:border-forest"><FileImage className="mx-auto text-forest" size={36}/><span className="mt-3 block font-bold">{t("report.photos")}</span><span className="mt-1 block text-xs text-slate-500">JPEG, PNG or WebP · 5 MB each · private by default</span><input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={chooseImages} disabled={images.length >= MAX_IMAGES}/></label>{mediaError && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-danger">{mediaError}</p>}{images.length > 0 && <ul className="grid gap-4 sm:grid-cols-3">{images.map((image, index) => <li className="overflow-hidden rounded-2xl border bg-white" key={`${image.file.name}-${image.file.lastModified}`}><div className="relative aspect-video"><Image src={image.preview} alt={`Preview of ${image.file.name}`} fill unoptimized className="object-cover"/></div><div className="flex items-center justify-between gap-2 p-3"><span className="min-w-0 truncate text-xs font-semibold">{image.file.name}</span><button className="rounded-lg p-2 text-danger hover:bg-red-50" type="button" onClick={() => removeImage(index)} aria-label={`${t("report.remove")} ${image.file.name}`}><X size={18}/></button></div></li>)}</ul>}</fieldset>}

      {step === 4 && <fieldset className="space-y-6"><legend className="text-2xl font-black">{t("report.step.reporter")}</legend><div className="grid gap-5 md:grid-cols-2"><label><span className="label">{t("report.name")}</span><input className="field" autoComplete="name" {...register("reporter_name")}/><small className="text-danger">{errors.reporter_name?.message}</small></label><label><span className="label">{t("report.phone")}</span><input className="field" type="tel" inputMode="tel" autoComplete="tel" {...register("contact_phone")}/><small className="text-danger">{errors.contact_phone?.message}</small></label><label className="md:col-span-2"><span className="label">{t("report.email")}</span><input className="field" type="email" autoComplete="email" {...register("reporter_email")}/><small className="text-danger">{errors.reporter_email?.message}</small></label></div><label className="flex items-start gap-3 rounded-xl border border-slate-300 p-4"><input className="mt-1 h-5 w-5 accent-green-700" type="checkbox" {...register("consent")}/><span className="text-sm leading-6 text-slate-700">{t("report.consent")}</span></label><small className="text-danger">{errors.consent?.message}</small></fieldset>}

      {step === 5 && <section className="space-y-6"><div className="flex items-center justify-between gap-4"><h2 className="text-2xl font-black">{t("report.step.review")}</h2><span className="rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-danger">DEMO ONLY</span></div><ReviewCard title={t("report.step.incident")} edit={() => setStep(0)}><p>{allValues.city}, {allValues.district}, {allValues.state}</p><p>{allValues.landmark || "No landmark"}</p><p className="mt-2 whitespace-pre-wrap text-slate-600">{allValues.description}</p></ReviewCard><ReviewCard title={t("report.step.triage")} edit={() => setStep(1)}><p>Injury/bite: {allValues.injury === "YES" ? t("common.yes") : t("common.no")} · Visible: {allValues.snake_visible === "YES" ? t("common.yes") : t("common.no")} · Immediate danger: {allValues.immediate_danger === "YES" ? t("common.yes") : t("common.no")}</p></ReviewCard><ReviewCard title={t("report.step.location")} edit={() => setStep(2)}><p>{latitude !== undefined && longitude !== undefined ? `${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)}${accuracy ? ` (±${Math.round(Number(accuracy))} m)` : ""}` : "Manual locality only; no GPS coordinates supplied."}</p></ReviewCard><ReviewCard title={t("report.step.media")} edit={() => setStep(3)}><p>{images.length ? `${images.length} private image${images.length === 1 ? "" : "s"} selected` : "No images selected"}</p></ReviewCard><ReviewCard title={t("report.step.reporter")} edit={() => setStep(4)}><p>{allValues.reporter_name} · {allValues.contact_phone}</p>{allValues.reporter_email && <p>{allValues.reporter_email}</p>}</ReviewCard><div className="rounded-xl bg-amber-50 p-4 text-sm font-semibold text-amber-950">{t("report.demo")}</div></section>}

      {errors.root && <p role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-danger">{errors.root.message}</p>}<div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t pt-6"><Button className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50" type="button" disabled={step === 0 || isSubmitting} onClick={() => setStep((current) => Math.max(0, current - 1))}><ChevronLeft size={18}/>{t("report.previous")}</Button>{step < steps.length - 1 ? <Button key="continue" type="button" onClick={next}>{t("report.next")}<ChevronRight size={18}/></Button> : <Button key="submit" type="button" onClick={handleSubmit(submit)} disabled={isSubmitting || submitLock.current}>{isSubmitting ? t("report.submitting") : t("report.submit")}<MapPin size={18}/></Button>}</div>
    </div>
  </form>;
}

function ReviewCard({title, edit, children}: {title: string; edit: () => void; children: React.ReactNode}) {
  const {t} = useI18n();
  return <article className="rounded-2xl border border-slate-200 p-5"><div className="mb-3 flex items-center justify-between gap-3"><h3 className="font-bold text-forest">{title}</h3><button type="button" onClick={edit} className="rounded-lg px-3 py-2 text-sm font-bold text-forest hover:bg-green-50">{t("report.edit")}</button></div><div className="text-sm leading-6 text-slate-700">{children}</div></article>;
}
