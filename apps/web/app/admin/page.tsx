import {PageHero} from "@/components/page-hero";
import {Dashboard} from "@/features/admin/dashboard";
export default function Admin(){return <><PageHero eyebrow="Restricted" title="Administration overview" description="Operational metrics are loaded from the protected API. Citizen contact and precise location fields are not included in this overview."/><section className="bg-mist py-12"><div className="container-page"><Dashboard/></div></section></>}

