import {useMemo, useRef, useState} from "react";
import {StyleSheet, View} from "react-native";
import {useRouter} from "expo-router";
import {Button, HelperText, Text} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import type {Incident} from "@/features/incidents/types";
import {useReportDraft} from "@/features/report/report-context";
import type {SelectedMedia} from "@/features/report/types";
import {toIncidentPayload, validateCompleteDraft} from "@/features/report/validation";
import {api, ApiError, uploadIncidentMedia} from "@/services/api";
import {localizedError} from "@/services/errors";
import {useI18n} from "@/services/i18n";

function SummarySection({title, value, onEdit}:{title:string;value:string;onEdit:()=>void}) {
  const {t} = useI18n();
  return (
    <View style={styles.summary}>
      <View style={styles.summaryText}><Text variant="titleSmall" style={styles.summaryTitle}>{title}</Text><Text>{value}</Text></View>
      <Button compact onPress={onEdit}>{t("edit")}</Button>
    </View>
  );
}

export default function ReportReview() {
  const router = useRouter();
  const {draft} = useReportDraft();
  const {t} = useI18n();
  const [submitting, setSubmitting] = useState(false);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [failedMedia, setFailedMedia] = useState<SelectedMedia[]>([]);
  const [error, setError] = useState("");
  const requestInFlight = useRef(false);
  const location = useMemo(() => [draft.city, draft.district, draft.state, draft.landmark].filter(Boolean).join(", "), [draft]);

  function finish(saved: Incident, failedCount = 0) {
    router.replace({pathname:"/report-confirmation", params:{id:saved.id, reference:saved.reference_code, uploadFailures:String(failedCount)}});
  }

  async function uploadAll(saved: Incident, files: SelectedMedia[]) {
    const failures: SelectedMedia[] = [];
    for (const file of files) {
      try {
        await uploadIncidentMedia(saved.id, file);
      } catch {
        failures.push(file);
      }
    }
    setFailedMedia(failures);
    return failures;
  }

  async function submit() {
    if (requestInFlight.current || incident) return;
    const issue = validateCompleteDraft(draft)[0];
    if (issue) {
      setError(issue.message);
      return;
    }
    requestInFlight.current = true;
    setSubmitting(true);
    setError("");
    try {
      const saved = await api<Incident>("/api/v1/incidents", {
        method:"POST",
        headers:{"Idempotency-Key":draft.idempotency_key},
        body:JSON.stringify(toIncidentPayload(draft)),
      });
      setIncident(saved);
      const failures = await uploadAll(saved, draft.media);
      if (!failures.length) finish(saved);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) setError(t("duplicatePrevented"));
      else setError(localizedError(requestError, t));
    } finally {
      requestInFlight.current = false;
      setSubmitting(false);
    }
  }

  async function retryUploads() {
    if (!incident || requestInFlight.current) return;
    requestInFlight.current = true;
    setSubmitting(true);
    setError("");
    try {
      const failures = await uploadAll(incident, failedMedia);
      if (!failures.length) finish(incident);
    } catch (uploadError) {
      setError(localizedError(uploadError, t));
    } finally {
      requestInFlight.current = false;
      setSubmitting(false);
    }
  }

  return (
    <Screen title={t("reviewTitle")} subtitle={t("reviewSubtitle")}>
      {draft.injury_reported && <InfoCard title={t("medicalTitle")} danger>{t("medicalGuidance")}</InfoCard>}
      <SummarySection title={t("description")} value={`${draft.sighting_at}\n${draft.description}`} onEdit={() => router.push("/report")} />
      <SummarySection title={t("triageTitle")} value={`Injury/bite: ${draft.injury_reported ? "Yes" : "No"}\nSnake visible: ${draft.snake_visible ? "Yes" : "No"}\nImmediate danger: ${draft.immediate_danger ? "Yes" : "No"}`} onEdit={() => router.push("/report-triage")} />
      <SummarySection title={t("location")} value={`${location}\n${draft.latitude == null ? "Manual locality only" : `${draft.latitude}, ${draft.longitude} · ±${draft.location_accuracy ?? "?"} m`}`} onEdit={() => router.push("/report-location")} />
      <SummarySection title={t("media")} value={`${draft.media.length} optional photo${draft.media.length === 1 ? "" : "s"}`} onEdit={() => router.push("/report-media")} />
      <SummarySection title={t("reporterTitle")} value={`${draft.reporter_name}\n${draft.contact_phone}\n${draft.reporter_email || "No email provided"}`} onEdit={() => router.push("/report-reporter")} />
      <InfoCard title="Demo submission">No live rescue dispatch or real emergency notification will occur.</InfoCard>
      {incident && failedMedia.length > 0 && <InfoCard title={t("uploadRetryTitle")}>{failedMedia.length} photo upload{failedMedia.length === 1 ? "" : "s"} failed. The demo incident itself was saved as {incident.reference_code}.</InfoCard>}
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      {!incident && <Button mode="contained" loading={submitting} disabled={submitting} contentStyle={styles.touchTarget} onPress={() => void submit()}>{submitting ? t("submitting") : t("submit")}</Button>}
      {incident && failedMedia.length > 0 && (
        <>
          <Button mode="contained" loading={submitting} disabled={submitting} onPress={() => void retryUploads()}>{t("retryUploads")}</Button>
          <Button mode="outlined" disabled={submitting} onPress={() => finish(incident, failedMedia.length)}>{t("continueWithoutPhotos")}</Button>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  summary: {alignItems:"flex-start", backgroundColor:"white", borderColor:"#e2e8f0", borderRadius:14, borderWidth:1, flexDirection:"row", gap:8, padding:14},
  summaryText: {flex:1, gap:6},
  summaryTitle: {fontWeight:"800", color:"#14532D"},
  touchTarget: {minHeight:48},
});
