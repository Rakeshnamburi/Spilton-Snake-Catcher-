import {ApiError} from "@/services/api";
import type {TranslationKey} from "@/services/i18n";

export function localizedError(error: unknown, t: (key: TranslationKey) => string) {
  if (error instanceof ApiError) {
    if (error.code === "SESSION_EXPIRED" || error.status === 401) return t("sessionExpired");
    if (error.code === "TIMEOUT") return t("timeoutError");
    if (error.code === "NETWORK_ERROR") return t("networkError");
    return error.message;
  }
  return error instanceof Error ? error.message : t("genericError");
}

