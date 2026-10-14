"use client";

import {useI18n} from "@/lib/i18n";
import {cn} from "@/lib/utils";

const colors: Record<string, string> = {
  CREATED: "bg-sky-100 text-sky-900",
  UNDER_REVIEW: "bg-amber-100 text-amber-900",
  ASSIGNED: "bg-violet-100 text-violet-900",
  IN_PROGRESS: "bg-indigo-100 text-indigo-900",
  RESOLVED: "bg-green-100 text-green-900",
  CLOSED: "bg-slate-200 text-slate-800",
  CANCELLED: "bg-red-100 text-red-900",
  UNABLE_TO_ASSIST: "bg-orange-100 text-orange-900",
};

export function IncidentStatusBadge({status, className}: {status: string; className?: string}) {
  const {t} = useI18n();
  return <span className={cn("inline-flex rounded-full px-3 py-1 text-xs font-bold", colors[status] ?? "bg-slate-100 text-slate-800", className)}>{t(`status.${status}`)}</span>;
}
