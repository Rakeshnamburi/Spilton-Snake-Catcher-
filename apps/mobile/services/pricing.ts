/**
 * Illustrative demo fare model (mobile).
 *
 * DEMO mode only: no money is collected and no invoice is issued. This only
 * produces a clearly-labelled estimate so the customer sees an approximate cost
 * up front. The real amount is recorded as a simulated cash/online payment.
 */

export const DEMO_TARIFF = {
  baseFare: 300,
  perKm: 25,
  minFare: 300,
  currency: "INR",
} as const;

export type FareEstimate = {
  baseFare: number;
  travelFare: number | null;
  total: number;
  distanceKm: number | null;
  currency: string;
};

export function estimateFare(distanceKm?: number | null): FareEstimate {
  const base = DEMO_TARIFF.baseFare;
  const hasDistance = typeof distanceKm === "number" && Number.isFinite(distanceKm);
  const travel = hasDistance ? Math.round((distanceKm as number) * DEMO_TARIFF.perKm) : null;
  return {
    baseFare: base,
    travelFare: travel,
    total: Math.max(DEMO_TARIFF.minFare, base + (travel ?? 0)),
    distanceKm: hasDistance ? (distanceKm as number) : null,
    currency: DEMO_TARIFF.currency,
  };
}

export function formatInr(value: number) {
  return `₹${value.toLocaleString("en-IN")}`;
}
