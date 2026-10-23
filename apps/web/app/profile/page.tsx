import {PageHero} from "@/components/page-hero";
import {ProfileManager} from "@/features/auth/profile";

export default function ProfilePage() {
  return <><PageHero eyebrow="Private account" title="Profile and privacy requests" description="Update your account details, revoke the current session, or submit a tracked data export/deletion request."/><div className="container-page py-12"><ProfileManager/></div></>;
}
