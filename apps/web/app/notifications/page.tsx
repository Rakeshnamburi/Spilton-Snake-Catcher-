import {PageHero} from "@/components/page-hero";
import {NotificationList} from "@/features/notifications/notification-list";
export default function NotificationsPage(){return <><PageHero eyebrow="Your updates" title="Notifications" description="Booking requests, rescuer responses, approvals and chat messages for your account."/><div className="container-page py-12"><NotificationList/></div></>;}
