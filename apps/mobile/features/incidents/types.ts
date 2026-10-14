export type IncidentStatus =
  | "CREATED"
  | "UNDER_REVIEW"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "CLOSED"
  | "CANCELLED"
  | "UNABLE_TO_ASSIST";

export type IncidentUrgency = "STANDARD" | "HIGH" | "SNAKEBITE";

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
  urgency: IncidentUrgency;
  status: IncidentStatus;
  is_demo: boolean;
  created_at: string;
  updated_at?: string;
  media?: IncidentMedia[];
};

export type IncidentListItem = Pick<
  Incident,
  | "id"
  | "reference_code"
  | "state"
  | "district"
  | "city"
  | "urgency"
  | "status"
  | "is_demo"
  | "sighting_at"
  | "created_at"
>;

export type IncidentEvent = {
  id: string;
  incident_id: string;
  event_type: string;
  details: string;
  created_at: string;
  from_status?: IncidentStatus | null;
  to_status?: IncidentStatus | null;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};
