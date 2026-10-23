import {PageHero} from "@/components/page-hero";
import {CustomerPayments} from "@/features/marketplace/day5-finance";
export default function PaymentsPage(){return <><PageHero eyebrow="Protected demo records" title="My demo payments" description="Review simulated no-charge, cash, or online records. No real funds are processed."/><div className="container-page py-12"><CustomerPayments/></div></>;}
