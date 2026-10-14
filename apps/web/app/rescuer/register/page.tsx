import {PageHero} from "@/components/page-hero";
import {RescuerOnboarding} from "@/features/marketplace/rescuer-onboarding";

export default function RescuerRegisterPage() {
  return <><PageHero eyebrow="Administrator-reviewed onboarding" title="Apply as an authorized rescuer" description="Submit a demo application and private evidence. Public signup never grants verification or real-world operating authority."/><div className="container-page py-12"><RescuerOnboarding/></div></>;
}
