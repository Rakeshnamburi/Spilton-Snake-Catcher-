import {PageHero} from "@/components/page-hero";
import {AdminBookings} from "@/features/admin/marketplace";

export default function AdminBookingsPage() {
  return <><PageHero eyebrow="Administrator and coordinator" title="Demo booking management" description="Inspect privacy-reduced simulated marketplace activity without exposing customer contact details or exact coordinates."/><div className="container-page py-12"><AdminBookings/></div></>;
}
