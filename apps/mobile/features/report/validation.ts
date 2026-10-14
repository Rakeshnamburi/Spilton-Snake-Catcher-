import type {IncidentCreatePayload, ReportDraft} from "@/features/report/types";
import {coordinatesAreInState, isTargetState, TARGET_REGIONS} from "@/services/regions";

export type ValidationIssue = {field: keyof ReportDraft | "form"; message: string};

export function validateIncidentStep(draft: ReportDraft): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (draft.description.trim().length < 10) {
    issues.push({field: "description", message: "Describe the sighting in at least 10 characters."});
  }
  const sightingTime = new Date(draft.sighting_at);
  if (Number.isNaN(sightingTime.getTime())) {
    issues.push({field: "sighting_at", message: "Enter a valid sighting date and time."});
  } else if (sightingTime.getTime() > Date.now() + 5 * 60_000) {
    issues.push({field: "sighting_at", message: "Sighting time cannot be in the future."});
  }
  return issues;
}

export function validateLocationStep(draft: ReportDraft): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (!isTargetState(draft.state)) {
    issues.push({field: "state", message: "Choose one of the five supported demo states."});
  } else if (!(TARGET_REGIONS[draft.state] as readonly string[]).includes(draft.district)) {
    issues.push({field: "district", message: "Choose a district for the selected state."});
  }
  if (draft.city.trim().length < 2) {
    issues.push({field: "city", message: "Enter a city or village."});
  }
  const oneCoordinateMissing = (draft.latitude == null) !== (draft.longitude == null);
  if (oneCoordinateMissing) {
    issues.push({field: "form", message: "Enter both latitude and longitude, or leave both blank."});
  } else if (draft.latitude != null && draft.longitude != null) {
    if (!Number.isFinite(draft.latitude) || !Number.isFinite(draft.longitude)) {
      issues.push({field: "form", message: "Enter numeric latitude and longitude values."});
    } else if (draft.latitude < -90 || draft.latitude > 90 || draft.longitude < -180 || draft.longitude > 180) {
      issues.push({field: "form", message: "Coordinates are outside valid latitude/longitude ranges."});
    } else if (isTargetState(draft.state) && !coordinatesAreInState(draft.state, draft.latitude, draft.longitude)) {
      issues.push({field: "form", message: "Coordinates appear outside the selected state. Review them before continuing."});
    }
  }
  if (draft.location_accuracy != null && (draft.latitude == null || draft.longitude == null)) {
    issues.push({field: "location_accuracy", message: "Location accuracy requires both latitude and longitude."});
  }
  if (draft.location_accuracy != null && (!Number.isFinite(draft.location_accuracy) || draft.location_accuracy < 0 || draft.location_accuracy > 10_000)) {
    issues.push({field: "location_accuracy", message: "Location accuracy must be between 0 and 10,000 metres."});
  }
  if (!draft.location_confirmed) {
    issues.push({field: "location_confirmed", message: "Confirm that you reviewed the location."});
  }
  return issues;
}

export function validateReporterStep(draft: ReportDraft): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (draft.reporter_name.trim().length < 2) issues.push({field: "reporter_name", message: "Enter your name."});
  if (!/^\+?[0-9]{10,15}$/.test(draft.contact_phone.trim())) {
    issues.push({field: "contact_phone", message: "Enter a 10–15 digit contact number."});
  }
  if (draft.reporter_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.reporter_email.trim())) {
    issues.push({field: "reporter_email", message: "Enter a valid email address or leave it blank."});
  }
  if (!draft.consent) issues.push({field: "consent", message: "Consent acknowledgement is required."});
  return issues;
}

export function validateCompleteDraft(draft: ReportDraft) {
  return [...validateIncidentStep(draft), ...validateLocationStep(draft), ...validateReporterStep(draft)];
}

export function toIncidentPayload(draft: ReportDraft): IncidentCreatePayload {
  const reporterEmail = draft.reporter_email.trim();
  const landmark = draft.landmark.trim();
  const addressDescription = draft.address_description.trim();
  return {
    reporter_name: draft.reporter_name.trim(),
    contact_phone: draft.contact_phone.trim(),
    reporter_email: reporterEmail || undefined,
    state: draft.state,
    district: draft.district,
    city: draft.city.trim(),
    landmark: landmark || undefined,
    address_description: addressDescription || undefined,
    latitude: draft.latitude,
    longitude: draft.longitude,
    location_accuracy: draft.location_accuracy,
    description: draft.description.trim(),
    sighting_at: new Date(draft.sighting_at).toISOString(),
    injury_reported: draft.injury_reported,
    snake_visible: draft.snake_visible,
    immediate_danger: draft.immediate_danger,
    urgency: draft.injury_reported ? "SNAKEBITE" : draft.immediate_danger ? "HIGH" : "STANDARD",
    consent: draft.consent,
  };
}
