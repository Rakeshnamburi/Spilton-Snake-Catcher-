import {PageHero} from "@/components/page-hero";
import {AdminTrackingSessions} from "@/features/admin/marketplace";

export default function AdminTrackingPage(){return <><PageHero eyebrow="Administrator only" title="Demo tracking sessions" description="Review session state, consent lifetime, and freshness without broadly exposing exact movement coordinates."/><div className="container-page py-12"><AdminTrackingSessions/></div></>}
