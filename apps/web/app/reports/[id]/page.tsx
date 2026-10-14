import {ReportDetail} from "@/features/incidents/report-detail";

export default async function ReportDetailPage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  return <section className="bg-mist py-12">
    <div className="container-page"><ReportDetail incidentId={id}/></div>
  </section>;
}
