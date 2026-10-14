import {createContext, ReactNode, useCallback, useContext, useMemo, useState} from "react";
import type {ReportDraft} from "@/features/report/types";

function localDateTimeValue(date = new Date()) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function makeIdempotencyKey() {
  const random = Math.random().toString(36).slice(2, 12);
  return `mobile-${Date.now().toString(36)}-${random}`;
}

function makeInitialDraft(): ReportDraft {
  return {
    description: "",
    sighting_at: localDateTimeValue(),
    injury_reported: false,
    snake_visible: false,
    immediate_danger: false,
    state: "",
    district: "",
    city: "",
    landmark: "",
    address_description: "",
    location_confirmed: false,
    media: [],
    reporter_name: "",
    contact_phone: "",
    reporter_email: "",
    consent: false,
    idempotency_key: makeIdempotencyKey(),
  };
}

type ReportContextValue = {
  draft: ReportDraft;
  update: <K extends keyof ReportDraft>(key: K, value: ReportDraft[K]) => void;
  patch: (values: Partial<ReportDraft>) => void;
  reset: () => void;
};

const ReportContext = createContext<ReportContextValue | null>(null);

export function ReportProvider({children}: {children: ReactNode}) {
  const [draft, setDraft] = useState<ReportDraft>(makeInitialDraft);
  const update = useCallback(function updateDraft<K extends keyof ReportDraft>(key: K, nextValue: ReportDraft[K]) {
    setDraft(current => ({...current, [key]: nextValue}));
  }, []);
  const patch = useCallback((values: Partial<ReportDraft>) => {
    setDraft(current => ({...current, ...values}));
  }, []);
  const reset = useCallback(() => setDraft(makeInitialDraft()), []);
  const value = useMemo<ReportContextValue>(() => ({
    draft,
    update,
    patch,
    reset,
  }), [draft, patch, reset, update]);
  return <ReportContext.Provider value={value}>{children}</ReportContext.Provider>;
}

export function useReportDraft() {
  const context = useContext(ReportContext);
  if (!context) throw new Error("useReportDraft must be used inside ReportProvider");
  return context;
}
