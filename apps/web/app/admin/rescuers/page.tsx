import {PageHero} from "@/components/page-hero";
import {AdminRescuers} from "@/features/admin/marketplace";

export default function AdminRescuersPage() {
  return <><PageHero eyebrow="Administrator only" title="Rescuer verification queue" description="Review private evidence, organization affiliation, expiry and the complete demo verification state machine."/><div className="container-page py-12"><AdminRescuers/></div></>;
}
