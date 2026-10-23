import {PageHero} from "@/components/page-hero";
import {RescuerJourney} from "@/features/tracking/rescuer-journey";

export default async function RescuerJourneyPage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  return <><PageHero eyebrow="Assigned demo journey" title="Foreground location sharing" description="Start only after explicit consent; pause or stop at any time. No background tracking or real dispatch occurs."/><div className="container-page py-12"><RescuerJourney id={id}/></div></>;
}
