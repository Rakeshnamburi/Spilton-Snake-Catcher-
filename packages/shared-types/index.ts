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
  | "UNABLE_TO_ASSIST"
  | "DISPUTED";

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
  /** How this profile covers the searched area; never exposes exact codes. */
  coverage_scope: "MANDAL" | "DISTRICT" | "STATE" | "OTHER" | null;
  eta_minutes: number | null;
}

export interface BookingEvent {
  id: string;
  event_type: string;
  details: string;
  sequence: number;
  created_at: string;
}

export type TrackingStatus = "ACTIVE" | "PAUSED" | "STOPPED" | "EXPIRED";

export interface TrackingLocation {
  id: string;
  latitude: number;
  longitude: number;
  accuracy: number;
  recorded_at: string;
  received_at: string;
  is_simulated: true;
}

export interface DemoRoute {
  status: "AVAILABLE" | "UNAVAILABLE";
  provider: string | null;
  road_distance_km: number | null;
  geographic_distance_km: number | null;
  duration_seconds: number | null;
  eta_at: string | null;
  coordinates: [number, number][];
  is_demo: true;
  message: string;
}

export interface BookingTracking {
  session_id: string | null;
  booking_id: string;
  status: TrackingStatus | null;
  consent_timestamp: string | null;
  started_at: string | null;
  paused_at: string | null;
  stopped_at: string | null;
  expires_at: string | null;
  last_location_at: string | null;
  latest_location: TrackingLocation | null;
  destination_latitude: number | null;
  destination_longitude: number | null;
  destination_precision: string;
  route: DemoRoute;
  is_demo: true;
  live_dispatch_enabled: false;
}

export interface BookingEventPage {
  items: BookingEvent[];
  last_sequence: number;
  heartbeat_seconds: number;
}

export interface NotificationItem {
  id: string;
  event_type: string;
  title: string;
  body: string;
  booking_id: string | null;
  deep_link: string | null;
  is_demo: true;
  read_at: string | null;
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
  quoted_amount: string | null;
  currency: string;
  commission_rate_snapshot: string;
  payment_status: "DISABLED" | "NOT_REQUIRED" | "PENDING" | "PAID" | "FAILED";
  is_demo: true;
  pricing_enabled: false;
  live_dispatch_enabled: false;
  accepted_at: string | null;
  responded_at: string | null;
  arrived_at: string | null;
  arrival_accuracy: number | null;
  arrival_review_warning: boolean;
  completed_at: string | null;
  customer_confirmed_at: string | null;
  expires_at: string;
  created_at: string;
  updated_at: string;
  events: BookingEvent[];
  history: BookingHistory[];
}

export interface RescueReport {
  id: string;
  booking_id: string;
  rescue_session_id: string;
  outcome_code: string;
  outcome_label: string;
  observations: string;
  authorized_action_summary: string;
  referral_details: string | null;
  notes: string | null;
  species_text: string | null;
  species_verification: string;
  completion_status: string;
  completed_at: string;
  is_demo: true;
}

export interface RescueEvidence {
  id: string;
  booking_id: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  evidence_type: string;
  captured_at: string | null;
  location_attached: boolean;
  retention_expires_at: string;
  created_at: string;
  is_demo: true;
}

export interface DemoPayment {
  id: string;
  payment_reference: string;
  booking_id: string;
  amount: string;
  currency: string;
  method: "DEMO_ONLINE" | "DEMO_CASH" | "NO_CHARGE";
  status: string;
  confirmed_at: string | null;
  refunded_amount: string;
  commission_rate: string | null;
  commission_amount: string | null;
  rescuer_share: string | null;
  is_demo: true;
  created_at: string;
}

export interface DemoReview {
  id: string;
  booking_id: string;
  rating: number;
  review_text: string | null;
  moderation_status: string;
  is_demo: true;
  created_at: string;
  updated_at: string;
}
