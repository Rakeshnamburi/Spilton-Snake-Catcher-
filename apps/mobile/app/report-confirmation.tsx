import {useEffect} from "react";
import {useLocalSearchParams, useRouter} from "expo-router";
import {Button, Text} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {useReportDraft} from "@/features/report/report-context";
import {useI18n} from "@/services/i18n";

export default function ReportConfirmation() {
  const router = useRouter();
  const params = useLocalSearchParams<{id?: string; reference?: string; uploadFailures?: string}>();
  const {reset} = useReportDraft();
  const {t} = useI18n();
  const failedUploads = Number(params.uploadFailures ?? "0");

  useEffect(() => {
    // A submitted draft must never be reused with the same idempotency key.
    reset();
  }, [reset]);

  return (
    <Screen title={t("confirmationTitle")} subtitle={t("confirmationMessage")}>
      <InfoCard title={t("reference")}>{params.reference ?? "Unavailable"}</InfoCard>
      {failedUploads > 0 && (
        <InfoCard title="Optional photos not saved">
          {failedUploads} optional photo upload{failedUploads === 1 ? "" : "s"} failed. The demo incident was still saved.
        </InfoCard>
      )}
      <Text variant="bodyMedium">Keep this reference for your records. Your signed-in account is still required to view the private report.</Text>
      {params.id && <Button mode="contained" onPress={() => router.replace(`/incidents/${params.id}`)}>{t("viewReport")}</Button>}
      <Button mode="outlined" onPress={() => router.replace("/my-reports")}>{t("reportsAction")}</Button>
      <Button onPress={() => router.replace("/report")}>{t("createAnother")}</Button>
    </Screen>
  );
}
