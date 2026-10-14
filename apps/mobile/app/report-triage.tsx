import {Linking, StyleSheet, View} from "react-native";
import {useRouter} from "expo-router";
import {Button, HelperText, RadioButton, Text} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {useReportDraft} from "@/features/report/report-context";
import {useI18n} from "@/services/i18n";

function BooleanQuestion({label, value, onChange}:{label:string;value:boolean;onChange:(value:boolean)=>void}) {
  const {t} = useI18n();
  return (
    <View style={styles.question} accessible accessibilityRole="radiogroup">
      <Text variant="titleSmall" style={styles.questionLabel}>{label}</Text>
      <View style={styles.radioRow}>
        <RadioButton.Item label={t("yes")} value="yes" status={value ? "checked" : "unchecked"} onPress={() => onChange(true)} style={styles.radio} />
        <RadioButton.Item label={t("no")} value="no" status={!value ? "checked" : "unchecked"} onPress={() => onChange(false)} style={styles.radio} />
      </View>
    </View>
  );
}

export default function ReportTriage() {
  const router = useRouter();
  const {draft, update} = useReportDraft();
  const {t, criticalTranslationsReviewed} = useI18n();

  return (
    <Screen title={t("triageTitle")} subtitle="Step 2 of 6 · Emergency medical assistance must never wait for this report.">
      <BooleanQuestion label={t("bittenQuestion")} value={draft.injury_reported} onChange={value => update("injury_reported", value)} />
      {draft.injury_reported && (
        <>
          <InfoCard title={t("medicalTitle")} danger>{t("medicalGuidance")}</InfoCard>
          {!criticalTranslationsReviewed && <HelperText type="info" visible>{t("criticalTranslationReview")}</HelperText>}
          <Button mode="contained" buttonColor="#DC2626" icon="phone" contentStyle={styles.touchTarget} onPress={() => void Linking.openURL("tel:112")}>{t("call112")}</Button>
        </>
      )}
      <BooleanQuestion label={t("visibleQuestion")} value={draft.snake_visible} onChange={value => update("snake_visible", value)} />
      <BooleanQuestion label={t("dangerQuestion")} value={draft.immediate_danger} onChange={value => update("immediate_danger", value)} />
      <Button mode="contained" contentStyle={styles.touchTarget} onPress={() => router.push("/report-location")}>{t("continueLocation")}</Button>
    </Screen>
  );
}

const styles = StyleSheet.create({
  question: {backgroundColor:"white", borderColor:"#e2e8f0", borderRadius:14, borderWidth:1, padding:12},
  questionLabel: {fontWeight:"700"},
  radioRow: {flexDirection:"row", flexWrap:"wrap"},
  radio: {minHeight:48, flex:1},
  touchTarget: {minHeight:48},
});
