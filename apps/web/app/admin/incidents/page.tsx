import {PageHero} from "@/components/page-hero";
import {Dashboard} from "@/features/admin/dashboard";

export default function AdminIncidentsPage() {
  return <><PageHero eyebrow="Protected administration" title="Demo incident queue" description="Review privacy-reduced Day 2 incidents and apply validated simulated status transitions."/><div className="container-page py-12"><Dashboard/></div></>;
}
