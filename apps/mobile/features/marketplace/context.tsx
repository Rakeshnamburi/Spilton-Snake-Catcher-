import {createContext, ReactNode, useContext, useMemo, useState} from "react";
import type {Booking, MarketplaceLocation, PublicRescuer} from "./types";

const EMPTY_LOCATION: MarketplaceLocation = {
  state_code: "",
  district_code: "",
  subdistrict_code: "",
  village_code: "",
  manualAddress: "",
  landmark: "",
};

type MarketplaceContextValue = {
  location: MarketplaceLocation;
  setLocation: (location: MarketplaceLocation) => void;
  selectedRescuer: PublicRescuer | null;
  setSelectedRescuer: (rescuer: PublicRescuer | null) => void;
  lastBooking: Booking | null;
  setLastBooking: (booking: Booking | null) => void;
};

const MarketplaceContext = createContext<MarketplaceContextValue | null>(null);

export function MarketplaceProvider({children}: {children: ReactNode}) {
  const [location, setLocation] = useState(EMPTY_LOCATION);
  const [selectedRescuer, setSelectedRescuer] = useState<PublicRescuer | null>(null);
  const [lastBooking, setLastBooking] = useState<Booking | null>(null);
  const value = useMemo(
    () => ({location, setLocation, selectedRescuer, setSelectedRescuer, lastBooking, setLastBooking}),
    [location, selectedRescuer, lastBooking],
  );
  return <MarketplaceContext.Provider value={value}>{children}</MarketplaceContext.Provider>;
}

export function useMarketplace() {
  const value = useContext(MarketplaceContext);
  if (!value) throw new Error("useMarketplace must be used inside MarketplaceProvider");
  return value;
}

export {EMPTY_LOCATION};
