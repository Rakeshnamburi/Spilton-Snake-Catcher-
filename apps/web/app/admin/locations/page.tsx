import {PageHero} from "@/components/page-hero";
import {AdminLocations} from "@/features/admin/marketplace";

export default function AdminLocationsPage() {
  return <><PageHero eyebrow="Administrator only" title="Official LGD import status" description="Review imported hierarchy counts, source versions and transactional job results. Empty data is reported honestly."/><div className="container-page py-12"><AdminLocations/></div></>;
}
