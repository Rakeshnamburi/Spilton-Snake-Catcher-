import {PageHero} from "@/components/page-hero";
import {RescuerBookings} from "@/features/marketplace/rescuer-bookings";

export default function RescuerBookingsPage() {
  return <><PageHero eyebrow="Simulated response queue" title="Incoming demo booking requests" description="Assigned fictional demo rescuers may accept or reject pending simulations. These actions never dispatch real assistance."/><div className="container-page py-12"><RescuerBookings/></div></>;
}
