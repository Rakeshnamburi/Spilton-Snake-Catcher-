export type Role="CITIZEN"|"RESCUER"|"COORDINATOR"|"ADMIN";
export type IncidentStatus=
  |"CREATED"
  |"UNDER_REVIEW"
  |"ASSIGNED"
  |"IN_PROGRESS"
  |"RESOLVED"
  |"CLOSED"
  |"CANCELLED"
  |"UNABLE_TO_ASSIST";
export type Urgency="STANDARD"|"HIGH"|"SNAKEBITE";
export interface ApiStatus {
  mode: "DEMO";
  operational_dispatch: false;
  authorized_operation: false;
  real_payments: false;
  external_rescue_notifications: false;
  message: string;
}

export interface IncidentCreatePayload {
  reporter_name:string;
  contact_phone:string;
  reporter_email?:string;
  state:string;
  district:string;
  city:string;
  landmark?:string;
  address_description?:string;
  latitude?:number;
  longitude?:number;
  location_accuracy?:number;
  description:string;
  sighting_at:string;
  injury_reported:boolean;
  snake_visible:boolean;
  immediate_danger:boolean;
  urgency:Urgency;
  consent:true;
}

export interface Paginated<T>{items:T[];total:number;page:number;page_size:number;pages:number}

export type RescuerVerificationStatus =
  | "PENDING"
  | "PENDING_VERIFICATION"
  | "UNDER_REVIEW"
  | "VERIFIED"
  | "REJECTED"
  | "SUSPENDED"
  | "EXPIRED";
export type AvailabilityStatus = "AVAILABLE" | "BUSY" | "OFFLINE";
export type BookingStatus =
  | "REQUESTED"
  | "PENDING_RESCUER_RESPONSE"
  | "ACCEPTED"
  | "REJECTED"
  | "EXPIRED"
  | "CANCELLED"
  | "EN_ROUTE"
  | "ARRIVED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "UNABLE_TO_ASSIST";

export interface MarketplacePage<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface LocationItem {
  id: string;
  lgd_code: string;
  name: string;
  local_name: string | null;
  is_active: boolean;
  source_version: string;
}

export interface PublicRescuer {
  id: string;
  display_name: string;
  organization: string;
  years_experience: number;
  languages: string[];
  service_area: string;
  availability: AvailabilityStatus;
  verification_status: RescuerVerificationStatus;
  authorization_expiry: string | null;
  average_rating: string;
  review_count: number;
  completed_service_count: number;
  distance_km: number | null;
  is_demo: true;
  pricing_enabled: false;
  service_charge: null;
  currency: "INR";
}

export interface BookingEvent {
  id: string;
  event_type: string;
  details: string;
  created_at: string;
}

export interface BookingHistory {
  id: string;
  previous_status: string | null;
  status: BookingStatus;
  note: string | null;
  created_at: string;
}

export interface Booking {
  id: string;
  booking_reference: string;
  customer_id: string;
  rescuer_id: string;
  rescuer_display_name: string;
  organization: string;
  incident_id: string | null;
  state_code: string | null;
  district_code: string | null;
  subdistrict_code: string | null;
  village_code: string | null;
  manual_address: string | null;
  landmark: string | null;
  latitude: number | null;
  longitude: number | null;
  location_accuracy: number | null;
  location_precision: "EXACT_OWNER_VIEW" | "APPROXIMATE_RESCUER_VIEW";
  customer_notes: string;
  status: BookingStatus;
  quoted_amount: null;
  currency: string;
  commission_rate_snapshot: string;
  payment_status: "DISABLED";
  is_demo: true;
  pricing_enabled: false;
  live_dispatch_enabled: false;
  accepted_at: string | null;
  responded_at: string | null;
  expires_at: string;
  created_at: string;
  updated_at: string;
  events: BookingEvent[];
  history: BookingHistory[];
}
