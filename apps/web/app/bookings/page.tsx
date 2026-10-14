import {PageHero} from "@/components/page-hero";
import {MyBookings} from "@/features/marketplace/bookings";

export default function BookingsPage() {
  return <><PageHero eyebrow="Protected customer area" title="My demo bookings" description="Track simulated requests, review status history, and cancel eligible bookings. Reference numbers alone never grant access."/><div className="container-page py-12"><MyBookings/></div></>;
}
