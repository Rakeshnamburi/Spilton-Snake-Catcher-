export const INCIDENT_STATUSES = [
  "CREATED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED", "UNABLE_TO_ASSIST",
] as const;
export type IncidentStatus = typeof INCIDENT_STATUSES[number];

export type IncidentMedia = {
  id: string;
  incident_id: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  uploaded_at: string;
  download_url: string;
};

export type Incident = {
  id: string;
  reference_code: string;
  reporter_name?: string;
  state: string;
  district: string;
  city: string;
  landmark?: string | null;
  address_description?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_accuracy?: number | null;
  description: string;
  sighting_at: string;
  injury_reported: boolean;
  snake_visible: boolean;
  immediate_danger: boolean;
  urgency: "STANDARD" | "HIGH" | "SNAKEBITE";
  status: IncidentStatus;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  media?: IncidentMedia[];
};

export type IncidentListItem = Pick<Incident,
  "id" | "reference_code" | "state" | "district" | "city" | "urgency" | "status" | "is_demo" | "sighting_at" | "created_at"
>;

export type AdminIncidentListItem = IncidentListItem & {
  injury_reported: boolean;
  immediate_danger: boolean;
};

export type IncidentEvent = {
  id: string;
  event_type: string;
  details?: string | null;
  created_at: string;
};

export type Page<T> = {items: T[]; total: number; page: number; page_size: number; pages: number};

export function normalizePage<T>(value: Page<T> | T[]): Page<T> {
  if (Array.isArray(value)) return {items: value, total: value.length, page: 1, page_size: value.length || 20, pages: 1};
  return value;
}

export function formatStatus(status: string) {
  return status.toLowerCase().split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function canCitizenCancel(status: IncidentStatus) {
  return status === "CREATED" || status === "UNDER_REVIEW";
}
