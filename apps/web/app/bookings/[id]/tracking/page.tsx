import {PageHero} from "@/components/page-hero";
import {CustomerTracking} from "@/features/tracking/customer-tracking";

export default async function TrackingPage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  return <><PageHero eyebrow="Consent-based simulation" title="Demo journey tracking" description="See private, authorized simulated updates. A stale or missing point is never presented as live."/><div className="container-page py-12"><CustomerTracking id={id}/></div></>;
}
