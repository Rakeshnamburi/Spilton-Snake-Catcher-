import {PageHero} from "@/components/page-hero";
import {RescuerDirectory} from "@/features/marketplace/rescuer-directory";

export default function RescuersPage() {
  return <><PageHero eyebrow="Day 3 demo marketplace" title="Nearby authorized-rescuer discovery foundation" description="Search fictional demo profiles that pass verification, organization, authorization-expiry, coverage, availability and distance checks. No live assistance is offered."/><div className="container-page py-12"><RescuerDirectory/></div></>;
}
