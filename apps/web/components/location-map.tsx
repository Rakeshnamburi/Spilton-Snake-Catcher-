"use client";

import {useEffect, useRef, useState} from "react";
import type {Map as MapLibreMap, Marker as MapLibreMarker} from "maplibre-gl";
import {MapPinOff} from "lucide-react";

type Props = {
  latitude?: number;
  longitude?: number;
  accuracy?: number;
  onChange: (latitude: number, longitude: number) => void;
};

const INDIA_CENTER: [number, number] = [78.5, 15.5];

export function LocationMap({latitude, longitude, accuracy, onChange}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerRef = useRef<MapLibreMarker | null>(null);
  const callbackRef = useRef(onChange);
  const [error, setError] = useState("");
  const hasCoordinates = Number.isFinite(latitude) && Number.isFinite(longitude);

  useEffect(() => {
    callbackRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let active = true;
    void import("maplibre-gl").then(({Map, Marker, NavigationControl}) => {
      if (!active || !containerRef.current) return;
      const center: [number, number] = hasCoordinates ? [longitude as number, latitude as number] : INDIA_CENTER;
      const map = new Map({
        container: containerRef.current,
        style: process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "https://demotiles.maplibre.org/style.json",
        center,
        zoom: hasCoordinates ? 14 : 4,
      });
      const marker = new Marker({draggable: true, color: "#DC2626"}).setLngLat(center).addTo(map);
      marker.on("dragend", () => {
        const point = marker.getLngLat();
        callbackRef.current(Number(point.lat.toFixed(6)), Number(point.lng.toFixed(6)));
      });
      map.addControl(new NavigationControl({showCompass: false}), "top-right");
      map.on("error", () => setError("Map tiles could not be loaded. Coordinates and manual location entry still work."));
      map.on("load", () => setError(""));
      mapRef.current = map;
      markerRef.current = marker;
    }).catch(() => setError("The interactive map could not start. Use the manual coordinates instead."));
    return () => {
      active = false;
      markerRef.current?.remove();
      mapRef.current?.remove();
      markerRef.current = null;
      mapRef.current = null;
    };
  // Create the map once; later coordinate updates are handled below.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hasCoordinates || !markerRef.current || !mapRef.current) return;
    const center: [number, number] = [longitude as number, latitude as number];
    markerRef.current.setLngLat(center);
    mapRef.current.easeTo({center, zoom: Math.max(mapRef.current.getZoom(), 13), duration: 500});
  }, [hasCoordinates, latitude, longitude]);

  return <div className="overflow-hidden rounded-2xl border border-slate-300 bg-slate-100">
    {error && <div role="alert" className="flex items-center gap-2 bg-amber-50 px-4 py-3 text-sm text-amber-900"><MapPinOff size={18}/>{error}</div>}
    <div ref={containerRef} className="h-72 w-full" role="application" aria-label="Interactive location map. Drag the marker to adjust coordinates."/>
    <div className="flex flex-wrap items-center justify-between gap-2 border-t bg-white px-4 py-3 text-xs text-slate-600">
      <span>Drag the red marker to refine the sighting location.</span>
      {Number.isFinite(accuracy) && <strong>GPS accuracy: ±{Math.round(accuracy as number)} m</strong>}
    </div>
  </div>;
}
