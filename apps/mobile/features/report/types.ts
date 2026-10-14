import type {IncidentUrgency} from "@/features/incidents/types";

export type SelectedMedia = {
  uri: string;
  fileName: string;
  mimeType: "image/jpeg" | "image/png" | "image/webp";
  fileSize: number;
};

export type ReportDraft = {
  description: string;
  sighting_at: string;
  injury_reported: boolean;
  snake_visible: boolean;
  immediate_danger: boolean;
  state: string;
  district: string;
  city: string;
  landmark: string;
  address_description: string;
  latitude?: number;
  longitude?: number;
  location_accuracy?: number;
  location_confirmed: boolean;
  media: SelectedMedia[];
  reporter_name: string;
  contact_phone: string;
  reporter_email: string;
  consent: boolean;
  idempotency_key: string;
};

export type IncidentCreatePayload = Omit<
  ReportDraft,
  | "media"
  | "location_confirmed"
  | "idempotency_key"
  | "sighting_at"
  | "reporter_email"
  | "landmark"
  | "address_description"
> & {
  sighting_at: string;
  urgency: IncidentUrgency;
  reporter_email?: string;
  landmark?: string;
  address_description?: string;
};
