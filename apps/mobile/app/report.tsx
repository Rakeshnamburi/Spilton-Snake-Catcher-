import {useState} from "react";
import {StyleSheet} from "react-native";
import {useRouter} from "expo-router";
import {Button, HelperText, TextInput} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {useReportDraft} from "@/features/report/report-context";
import {validateIncidentStep} from "@/features/report/validation";
import {useI18n} from "@/services/i18n";

export default function Report() {
  const router = useRouter();
  const {draft, update} = useReportDraft();
  const {t} = useI18n();
  const [error, setError] = useState("");

  function next() {
    const issue = validateIncidentStep(draft)[0];
    if (issue) {
      setError(issue.message);
      return;
    }
    setError("");
    router.push("/report-triage");
  }

  return (
    <Screen title={t("incidentTitle")} subtitle={t("incidentSubtitle")}>
      <InfoCard title="Safe reporting">Never approach, touch, trap, catch, or relocate the snake. GPS and photos are optional.</InfoCard>
      <TextInput
        label={`${t("sightingTime")} *`}
        value={draft.sighting_at}
        onChangeText={value => update("sighting_at", value)}
        placeholder="YYYY-MM-DDTHH:mm"
        autoCapitalize="none"
      />
      <TextInput
        label={`${t("description")} *`}
        value={draft.description}
        onChangeText={value => update("description", value)}
        multiline
        numberOfLines={5}
        maxLength={2000}
      />
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      <Button mode="contained" contentStyle={styles.touchTarget} onPress={next}>{t("continueTriage")}</Button>
    </Screen>
  );
}

const styles = StyleSheet.create({
  touchTarget: {minHeight:48},
});
