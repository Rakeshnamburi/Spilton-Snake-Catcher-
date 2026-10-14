"use client";

import {useEffect, useState} from "react";
import {api} from "@/lib/api";
import type {LocationItem, MarketplacePage} from "@/lib/marketplace";

export type DirectoryLocation = {
  state_code: string;
  district_code: string;
  subdistrict_code: string;
  village_code: string;
};

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
  const [villages, setVillages] = useState<LocationItem[]>([]);
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

  useEffect(() => {
    if (!value.subdistrict_code) {
      setVillages([]);
      return;
    }
    api<MarketplacePage<LocationItem>>(
      `/api/v1/locations/villages?subdistrict_code=${encodeURIComponent(value.subdistrict_code)}&limit=100`,
    )
      .then((result) => setVillages(result.items))
      .catch(() => setVillages([]));
  }, [value.subdistrict_code]);

  function update(next: Partial<DirectoryLocation>) {
    onChange({...value, ...next});
  }

  return <div className="space-y-4">
    <div className="grid gap-4 md:grid-cols-2">
      <label><span className="label">State / Union Territory</span><select className="field" required={required} value={value.state_code} onChange={(event) => update({state_code: event.target.value, district_code: "", subdistrict_code: "", village_code: ""})}><option value="">Select imported LGD state</option>{states.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}</select></label>
      <label><span className="label">District</span><select className="field" required={required} disabled={!value.state_code} value={value.district_code} onChange={(event) => update({district_code: event.target.value, subdistrict_code: "", village_code: ""})}><option value="">Select district</option>{districts.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}</select></label>
      <label><span className="label">Subdistrict / mandal / taluk / tehsil</span><select className="field" disabled={!value.district_code} value={value.subdistrict_code} onChange={(event) => update({subdistrict_code: event.target.value, village_code: ""})}><option value="">Optional subdistrict</option>{subdistricts.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}</select></label>
      <label><span className="label">Village</span><select className="field" disabled={!value.subdistrict_code} value={value.village_code} onChange={(event) => update({village_code: event.target.value})}><option value="">Optional village</option>{villages.map((item) => <option key={item.lgd_code} value={item.lgd_code}>{item.name}</option>)}</select></label>
    </div>
    {!states.length && !error && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">No official LGD directory has been imported yet. An administrator must load current Government of India LGD exports before directory selection is available.</p>}
    {error && <p className="text-sm font-semibold text-danger" role="alert">{error}</p>}
    <p className="text-xs leading-5 text-slate-500">Directory labels come from the imported official LGD export. GPS coordinates are not treated as a verified village address; confirm or correct the selectors yourself.</p>
  </div>;
}

export const EMPTY_DIRECTORY_LOCATION: DirectoryLocation = {
  state_code: "",
  district_code: "",
  subdistrict_code: "",
  village_code: "",
};
