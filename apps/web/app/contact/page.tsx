import {PageHero} from "@/components/page-hero";
import {EnquiryForm} from "@/features/contact/enquiry-form";

export default function Contact() {
  return <>
    <PageHero
      eyebrow="Contact"
      title="Partnership and project enquiries"
      description="Send us a message and we reply to the address you give. This form is for enquiries only, never for emergencies."
    />
    <section className="bg-mist py-16"><div className="container-page"><EnquiryForm/></div></section>
  </>;
}
