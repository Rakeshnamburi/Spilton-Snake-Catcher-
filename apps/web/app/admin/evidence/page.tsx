import {PageHero} from "@/components/page-hero";
import {AdminEvidence} from "@/features/admin/day5";
export default function Page(){return <><PageHero eyebrow="Restricted private media" title="Evidence retention review" description="Sanitized file metadata only; exact coordinates and storage keys remain hidden."/><div className="container-page py-12"><AdminEvidence/></div></>;}
