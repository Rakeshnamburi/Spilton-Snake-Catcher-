import {PageHero} from "@/components/page-hero";
import {AdminAccountRequests} from "@/features/admin/account-requests";

export default function AdminAccountRequestsPage(){return <><PageHero eyebrow="Administrator only" title="Privacy request queue" description="Review tracked account export and deletion requests with an auditable status workflow."/><div className="container-page py-12"><AdminAccountRequests/></div></>}
