export type {
  AvailabilityStatus,
  Booking,
  BookingStatus,
  LocationItem,
  MarketplacePage,
  PublicRescuer,
  RescuerVerificationStatus,
} from "@spilton/shared-types";

export function humanize(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {dateStyle: "medium", timeStyle: "short"}).format(
    new Date(value),
  );
}
