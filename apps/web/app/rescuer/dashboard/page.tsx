import {PageHero} from "@/components/page-hero";
import {RescuerDashboard} from "@/features/marketplace/rescuer-dashboard";

export default function RescuerDashboardPage() {
  return <><PageHero eyebrow="Protected rescuer workspace" title="Rescuer dashboard" description="View administrator-controlled verification, simulated availability and in-app demo notifications."/><div className="container-page py-12"><RescuerDashboard/></div></>;
}
