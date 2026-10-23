import {PageHero} from "@/components/page-hero";
import {AdminPayments} from "@/features/admin/day5";
export default function Page(){return <><PageHero eyebrow="Restricted demo finance" title="Payment ledger overview" description="Illustrative amounts only; no real payments or payouts."/><div className="container-page py-12"><AdminPayments/></div></>;}
