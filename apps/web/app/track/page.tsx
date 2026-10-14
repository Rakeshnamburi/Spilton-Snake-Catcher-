import {PageHero} from "@/components/page-hero";
import {TrackForm} from "@/features/incidents/track-form";
export default function Track(){return <><PageHero eyebrow="Private tracking" title="Track your demo incident" description="Sign in and enter the reference. Account ownership is verified before any incident information is shown."/><section className="bg-mist py-14"><div className="container-page"><TrackForm/></div></section></>}

