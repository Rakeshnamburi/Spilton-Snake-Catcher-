import type {IncidentStatus} from "@/features/incidents/types";
import type {TranslationKey} from "@/services/i18n";

export const STATUS_TRANSLATION_KEYS: Record<IncidentStatus, TranslationKey> = {
  CREATED: "statusCREATED",
  UNDER_REVIEW: "statusUNDER_REVIEW",
  ASSIGNED: "statusASSIGNED",
  IN_PROGRESS: "statusIN_PROGRESS",
  RESOLVED: "statusRESOLVED",
  CLOSED: "statusCLOSED",
  CANCELLED: "statusCANCELLED",
  UNABLE_TO_ASSIST: "statusUNABLE_TO_ASSIST",
};

export const CANCELLABLE_STATUSES: IncidentStatus[] = ["CREATED", "UNDER_REVIEW"];

