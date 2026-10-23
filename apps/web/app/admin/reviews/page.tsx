import {PageHero} from "@/components/page-hero";
import {AdminReviews} from "@/features/admin/day5";
export default function Page(){return <><PageHero eyebrow="Restricted moderation" title="Demo reviews" description="Publish, hide, or remove customer-submitted simulated reviews."/><div className="container-page py-12"><AdminReviews/></div></>;}
