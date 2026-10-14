import {PageHero} from "@/components/page-hero";
import {RescuerProfileView} from "@/features/marketplace/rescuer-profile";

export default async function RescuerProfilePage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  return <><PageHero eyebrow="Fictional demo profile" title="Rescuer profile" description="Review simulated eligibility and service coverage before creating a demo-only request."/><div className="container-page py-12"><RescuerProfileView id={id}/></div></>;
}
