"use client";

import {useEffect, useRef, useState} from "react";
import type {GeoJSONSource, Map as MapLibreMap, Marker} from "maplibre-gl";
import {MapPinOff} from "lucide-react";

type Point = {latitude: number; longitude: number};

export function TrackingMap({rescuer, destination, route}: {
  rescuer: Point | null;
  destination: Point | null;
  route: [number, number][];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const rescuerMarker = useRef<Marker | null>(null);
  const destinationMarker = useRef<Marker | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let active = true;
    void import("maplibre-gl").then(({Map, NavigationControl}) => {
      if (!active || !containerRef.current) return;
      const initial = rescuer ?? destination ?? {latitude: 15.5, longitude: 78.5};
      const map = new Map({
        container: containerRef.current,
        style: process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "https://demotiles.maplibre.org/style.json",
        center: [initial.longitude, initial.latitude],
        zoom: rescuer || destination ? 13 : 4,
      });
      map.addControl(new NavigationControl({showCompass: false}), "top-right");
      map.on("error", () => setError("Map tiles are unavailable. Status and timestamps still work."));
      map.on("load", () => setError(""));
      mapRef.current = map;
    }).catch(() => setError("The tracking map could not start."));
    return () => {
      active = false;
      rescuerMarker.current?.remove();
      destinationMarker.current?.remove();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  // Map creation is intentionally one-time; the next effect updates live data.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    void import("maplibre-gl").then(({Marker}) => {
      if (rescuer) {
        rescuerMarker.current ??= new Marker({color: "#16A34A"}).addTo(map);
        rescuerMarker.current.setLngLat([rescuer.longitude, rescuer.latitude]);
      } else {
        rescuerMarker.current?.remove();
        rescuerMarker.current = null;
      }
      if (destination) {
        destinationMarker.current ??= new Marker({color: "#DC2626"}).addTo(map);
        destinationMarker.current.setLngLat([destination.longitude, destination.latitude]);
      }
      const center = rescuer ?? destination;
      if (center) map.easeTo({center: [center.longitude, center.latitude], duration: 500});
      const geojson = {
        type: "Feature" as const,
        properties: {},
        geometry: {type: "LineString" as const, coordinates: route},
      };
      const applyRoute = () => {
        const source = map.getSource("demo-route") as GeoJSONSource | undefined;
        if (source) source.setData(geojson);
        else {
          map.addSource("demo-route", {type: "geojson", data: geojson});
          map.addLayer({
            id: "demo-route-line",
            type: "line",
            source: "demo-route",
            paint: {"line-color": "#14532D", "line-width": 5, "line-opacity": 0.75},
          });
        }
      };
      if (map.isStyleLoaded()) applyRoute();
      else map.once("load", applyRoute);
    });
  }, [destination, rescuer, route]);

  return <div className="overflow-hidden rounded-2xl border border-slate-300 bg-slate-100">
    {error && <div role="alert" className="flex items-center gap-2 bg-amber-50 px-4 py-3 text-sm text-amber-950"><MapPinOff size={18}/>{error}</div>}
    <div ref={containerRef} className="h-[420px] w-full" aria-label="Simulated booking tracking map"/>
    <div className="flex flex-wrap gap-4 border-t bg-white px-4 py-3 text-xs font-bold text-slate-600"><span><i className="mr-2 inline-block h-3 w-3 rounded-full bg-emerald"/>Last simulated rescuer point</span><span><i className="mr-2 inline-block h-3 w-3 rounded-full bg-danger"/>Customer destination</span></div>
  </div>;
}
