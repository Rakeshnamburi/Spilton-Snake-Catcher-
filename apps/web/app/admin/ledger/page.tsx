import {PageHero} from "@/components/page-hero";
import {AdminLedger} from "@/features/admin/day5";
export default function Page(){return <><PageHero eyebrow="Restricted demo accounting" title="Financial ledger" description="Balanced illustrative entries with no settlement or payout."/><div className="container-page py-12"><AdminLedger/></div></>;}
