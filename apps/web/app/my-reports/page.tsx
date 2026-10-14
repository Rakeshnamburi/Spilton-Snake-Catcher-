import {PageHero} from "@/components/page-hero";
import {MyReports} from "@/features/incidents/my-reports";

export default function MyReportsPage() {
  return <>
    <PageHero
      eyebrow="Private account area"
      title="My reports"
      description="Review only the demo incidents connected to your signed-in account. Precise locations and report details are never published here."
    />
    <section className="bg-mist py-12">
      <div className="container-page"><MyReports/></div>
    </section>
  </>;
}
