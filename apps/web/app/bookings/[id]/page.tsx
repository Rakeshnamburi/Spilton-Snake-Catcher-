import {PageHero} from "@/components/page-hero";
import {BookingDetail} from "@/features/marketplace/bookings";

export default async function BookingDetailPage({params, searchParams}: {params: Promise<{id: string}>; searchParams: Promise<{created?: string}>}) {
  const [{id}, query] = await Promise.all([params, searchParams]);
  return <><PageHero eyebrow="Demo request status" title="Booking details" description="This protected timeline reflects simulated marketplace actions only. No live dispatch or payment occurs."/><div className="container-page py-12"><BookingDetail id={id} created={query.created === "1"}/></div></>;
}
