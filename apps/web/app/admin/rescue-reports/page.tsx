import {PageHero} from "@/components/page-hero";
import {AdminRescueReports} from "@/features/admin/day5";
export default function Page(){return <><PageHero eyebrow="Restricted demo review" title="Rescue completion reports" description="Privacy-reduced simulated outcomes and evidence counts."/><div className="container-page py-12"><AdminRescueReports/></div></>;}
