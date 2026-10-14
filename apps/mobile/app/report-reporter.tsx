import {useEffect, useState} from "react";
import {StyleSheet} from "react-native";
import {useRouter} from "expo-router";
import {Button, Checkbox, HelperText, TextInput} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {useReportDraft} from "@/features/report/report-context";
import {validateReporterStep} from "@/features/report/validation";
import {api, ApiError} from "@/services/api";
import {useI18n} from "@/services/i18n";

type CurrentUser = {name:string; email:string; phone:string};
type AccountState = "checking" | "signed-in" | "signed-out" | "error";

export default function ReportReporter() {
  const router = useRouter();
  const {draft, patch, update} = useReportDraft();
  const {t} = useI18n();
  const [error, setError] = useState("");
  const [accountState, setAccountState] = useState<AccountState>("checking");

  useEffect(() => {
    let active = true;
    api<CurrentUser>("/api/v1/auth/me").then(user => {
      if (!active) return;
      setAccountState("signed-in");
      patch({
        reporter_name: draft.reporter_name || user.name,
        contact_phone: draft.contact_phone || user.phone,
        reporter_email: draft.reporter_email || user.email,
      });
    }).catch(requestError => {
      if (!active) return;
      if (requestError instanceof ApiError && requestError.status === 401) {
        setAccountState("signed-out");
      } else {
        setAccountState("error");
        setError(requestError instanceof Error ? requestError.message : t("genericError"));
      }
    });
    return () => { active = false; };
    // Prefill once on entry; subsequent edits must not be overwritten.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function next() {
    const issue = validateReporterStep(draft)[0];
    if (issue) {
      setError(issue.message);
      return;
    }
    if (accountState === "signed-out") {
      setError("Sign in with a citizen account before submitting this private demo report.");
      return;
    }
    if (accountState !== "signed-in") {
      setError("Your account could not be verified. Check your connection and try again.");
      return;
    }
    setError("");
    router.push("/report-review");
  }

  return (
    <Screen title={t("reporterTitle")} subtitle={t("reporterSubtitle")}>
      {accountState === "signed-out" && (
        <InfoCard title="Citizen account required">Sign in or register so the private report can only be viewed by its owner and authorized coordinators.</InfoCard>
      )}
      <TextInput label={`${t("reporterName")} *`} value={draft.reporter_name} onChangeText={value => update("reporter_name", value)} maxLength={120} />
      <TextInput label={`${t("contactPhone")} *`} value={draft.contact_phone} onChangeText={value => update("contact_phone", value.replace(/[\s()-]/g, ""))} keyboardType="phone-pad" maxLength={16} />
      <TextInput label={t("reporterEmail")} value={draft.reporter_email} onChangeText={value => update("reporter_email", value)} keyboardType="email-address" autoCapitalize="none" maxLength={254} />
      <Checkbox.Item label={t("consent")} status={draft.consent ? "checked" : "unchecked"} onPress={() => update("consent", !draft.consent)} />
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      {accountState === "signed-out" && <Button mode="outlined" onPress={() => router.replace({pathname:"/login", params:{returnTo:"report"}})}>{t("signIn")}</Button>}
      <Button mode="contained" disabled={accountState === "checking"} loading={accountState === "checking"} contentStyle={styles.touchTarget} onPress={next}>{t("continueReview")}</Button>
    </Screen>
  );
}

const styles = StyleSheet.create({touchTarget:{minHeight:48}});
