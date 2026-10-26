"use client";

import {useEffect, useRef, useState} from "react";
import {Search} from "lucide-react";
import {api} from "@/lib/api";
import type {LocationItem, MarketplacePage} from "@/lib/marketplace";

export type DirectoryLocation = {
  state_code: string;
  district_code: string;
  subdistrict_code: string;
  village_code: string;
};

/**
 * Village / town picker.
 *
 * A district can hold more than a thousand villages, so a plain <select> is
 * unusable. This is a searchable combobox: pick a district and the first
 * villages appear; type to search the whole district by name.
 */
function VillagePicker({
  districtCode,
  subdistrictCode,
  value,
  onChange,
}: {
  districtCode: string;
  subdistrictCode: string;
  value: string;
  onChange: (code: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<LocationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const enabled = Boolean(districtCode || subdistrictCode);

  useEffect(() => {
    if (!enabled) {
      setOptions([]);
      setTotal(0);
      return;
    }
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({limit: "50"});
      if (subdistrictCode) params.set("subdistrict_code", subdistrictCode);
      else params.set("district_code", districtCode);
      if (query.trim()) params.set("q", query.trim());
      setLoading(true);
      api<MarketplacePage<LocationItem>>(`/api/v1/locations/villages?${params}`)
        .then((result) => {
          setOptions(result.items);
          setTotal(result.total);
        })
        .catch(() => {
          setOptions([]);
          setTotal(0);
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [districtCode, subdistrictCode, query, enabled]);

  useEffect(() => {
    function onOutside(event: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  const selected = options.find((item) => item.lgd_code === value);

  return <div className="relative" ref={boxRef}>
    <span className="label">Village or town</span>
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16}/>
      <input
        className="field pl-9"
        disabled={!enabled}
        placeholder={enabled ? "Type a village name to search…" : "Select a district first"}
        value={open ? query : selected?.name ?? query}
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value);
          onChange("");
          setOpen(true);
        }}
        aria-label="Village or town"
        autoComplete="off"
      />
    </div>
    {open && enabled && <div className="absolute z-50 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl">
      {loading && <p className="px-3 py-2 text-sm text-slate-500">Searching…</p>}
      {!loading && options.length === 0 && <p className="px-3 py-2 text-sm text-slate-500">No village matched. Try fewer letters.</p>}
      {options.map((item) => <button
        key={item.lgd_code}
        type="button"
        className={`block w-full px-3 py-2 text-left text-sm hover:bg-mist ${item.lgd_code === value ? "bg-mist font-bold text-forest" : ""}`}
        onClick={() => {
          onChange(item.lgd_code);
          setQuery(item.name);
          setOpen(false);
        }}
      >
        {item.name}
      </button>)}
      {total > options.length && <p className="border-t border-slate-100 px-3 py-2 text-xs text-slate-500">Showing {options.length} of {total}. Type more letters to narrow it down.</p>}
    </div>}
    {!enabled && <p className="mt-1 text-xs text-slate-500">Choose a state and district first.</p>}
  </div>;
}

export function LocationSelector({
  value,
  onChange,
  required = false,
}: {
  value: DirectoryLocation;
  onChange: (value: DirectoryLocation) => void;
  required?: boolean;
}) {
  const [states, setStates] = useState<LocationItem[]>([]);
  const [districts, setDistricts] = useState<LocationItem[]>([]);
  const [subdistricts, setSubdistricts] = useState<LocationItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<MarketplacePage<LocationItem>>("/api/v1/locations/states?limit=100")
      .then((result) => setStates(result.items))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Location directory unavailable."));
  }, []);

  useEffect(() => {
    if (!value.state_code) {
      setDistricts([]);
      return;
    }
    api<MarketplacePage<LocationItem>>(
      `/api/v1/locations/districts?state_code=${encodeURIComponent(value.state_code)}&limit=100`,
    )
      .then((result) => setDistricts(result.items))
      .catch(() => setDistricts([]));
  }, [value.state_code]);

  useEffect(() => {
    if (!value.district_code) {
      setSubdistricts([]);
      return;
    }
    api<MarketplacePage<LocationItem>>(
      `/api/v1/locations/subdistricts?district_code=${encodeURIComponent(value.district_code)}&limit=100`,
    )
      .then((result) => setSubdistricts(result.items))
      .catch(() => setSubdistricts([]));
  }, [value.district_code]);

  function update(next: Partial<DirectoryLocation>) {
    onChange({...value, ...next});
  }

  return <div className="space-y-4">
    <div className="grid gap-4 md:grid-cols-2">
      <label>
        <span className="label">State / Union Territory</span>
        <select className="field" required={required} value={value.state_code} onChange={(event) => update({state_code: event.target.value, district_code: "", subdistrict_code: "", village_code: ""})}>
          <option value="">Select state</option>
          {states.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}
        </select>
      </label>
      <label>
        <span className="label">District</span>
        <select className="field" required={required} disabled={!value.state_code} value={value.district_code} onChange={(event) => update({district_code: event.target.value, subdistrict_code: "", village_code: ""})}>
          <option value="">{value.state_code ? "Select district" : "Select a state first"}</option>
          {districts.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}
        </select>
      </label>
      <label>
        <span className="label">Mandal / taluk / tehsil</span>
        <select className="field" disabled={!value.district_code} value={value.subdistrict_code} onChange={(event) => update({subdistrict_code: event.target.value, village_code: ""})}>
          <option value="">{value.district_code ? `All mandals in ${districts.find((d) => d.lgd_code === value.district_code)?.name ?? "this district"}` : "Select a district first"}</option>
          {subdistricts.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}
        </select>
      </label>
      <VillagePicker
        districtCode={value.district_code}
        subdistrictCode={value.subdistrict_code}
        value={value.village_code}
        onChange={(code) => update({village_code: code})}
      />
    </div>
    {!states.length && !error && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">No LGD directory loaded yet. Run <code>python -m app.db.load_lgd</code> in services/api to load the bundled location data.</p>}
    {error && <p className="text-sm font-semibold text-danger" role="alert">{error}</p>}
    <p className="text-xs leading-5 text-slate-500">Pick a district to see its villages, or choose a mandal first to narrow the list. Village is optional — a district-level booking is allowed.</p>
  </div>;
}

export const EMPTY_DIRECTORY_LOCATION: DirectoryLocation = {
  state_code: "",
  district_code: "",
  subdistrict_code: "",
  village_code: "",
};
