import {PageHero} from "@/components/page-hero";
import {AdminNotificationDeliveries} from "@/features/admin/marketplace";

export default function AdminNotificationsPage(){return <><PageHero eyebrow="Administrator only" title="Notification delivery status" description="Inspect sanitized in-app and provider-adapter results without exposing recipients, tokens, credentials, or message bodies."/><div className="container-page py-12"><AdminNotificationDeliveries/></div></>}
