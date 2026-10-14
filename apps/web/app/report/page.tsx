import {PageHero} from "@/components/page-hero";
import {ReportForm} from "@/features/incidents/report-form";
export default function Report(){return <><PageHero eyebrow="Demo reporting" title="Report a snake sighting" description="Record what you observed without moving closer. You must sign in first so private location and contact details remain account-protected."/><section className="bg-mist py-12"><div className="container-page"><ReportForm/></div></section></>}

