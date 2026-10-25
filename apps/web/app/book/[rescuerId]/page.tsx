import {PageHero} from "@/components/page-hero";
import {BookingForm} from "@/features/marketplace/booking-form";

export default async function BookRescuerPage({
  params,
  searchParams,
}: {
  params: Promise<{rescuerId: string}>;
  searchParams: Promise<{distance?: string}>;
}) {
  const {rescuerId} = await params;
  const {distance} = await searchParams;
  const parsed = Number(distance);
  const distanceKm = Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
  return <><PageHero eyebrow="Simulated request" title="Request demo assistance" description="Confirm a location, describe the situation from a safe distance, review the summary, and create a demo booking. No live dispatch or payment occurs."/><div className="container-page py-12"><BookingForm rescuerId={rescuerId} distanceKm={distanceKm}/></div></>;
}
