import {useState} from "react";
import {ScrollView, StyleSheet} from "react-native";
import * as Location from "expo-location";
import {useRouter} from "expo-router";
import {Button, Checkbox, Dialog, HelperText, Portal, RadioButton, Text, TextInput} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {useReportDraft} from "@/features/report/report-context";
import {validateLocationStep} from "@/features/report/validation";
import {TARGET_REGIONS, TARGET_STATES, type TargetState} from "@/services/regions";
import {useI18n} from "@/services/i18n";

type LocationState = "idle" | "requesting" | "success" | "denied" | "timeout" | "error";

function ChoiceDialog({visible, title, choices, value, onDismiss, onSelect}:{
  visible:boolean; title:string; choices:readonly string[]; value:string; onDismiss:()=>void; onSelect:(choice:string)=>void;
}) {
  return (
    <Portal>
      <Dialog visible={visible} onDismiss={onDismiss}>
        <Dialog.Title>{title}</Dialog.Title>
        <Dialog.ScrollArea style={styles.dialogArea}>
          <ScrollView>
            {choices.map(choice => <RadioButton.Item key={choice} label={choice} value={choice} status={choice === value ? "checked" : "unchecked"} onPress={() => onSelect(choice)} />)}
          </ScrollView>
        </Dialog.ScrollArea>
        <Dialog.Actions><Button onPress={onDismiss}>Close</Button></Dialog.Actions>
      </Dialog>
    </Portal>
  );
}

async function getPositionWithTimeout() {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      Location.getCurrentPositionAsync({accuracy:Location.Accuracy.High}),
      new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error("LOCATION_TIMEOUT")), 15_000); }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export default function ReportLocation() {
  const router = useRouter();
  const {draft, patch, update} = useReportDraft();
  const {t} = useI18n();
  const [stateDialog, setStateDialog] = useState(false);
  const [districtDialog, setDistrictDialog] = useState(false);
  const [locationState, setLocationState] = useState<LocationState>("idle");
  const [latitude, setLatitude] = useState(draft.latitude?.toString() ?? "");
  const [longitude, setLongitude] = useState(draft.longitude?.toString() ?? "");
  const [accuracy, setAccuracy] = useState(draft.location_accuracy?.toString() ?? "");
  const [error, setError] = useState("");
  const selectedState = TARGET_STATES.includes(draft.state as TargetState) ? draft.state as TargetState : undefined;
  const districts = selectedState ? TARGET_REGIONS[selectedState] : [];

  async function locate() {
    setError("");
    setLocationState("requesting");
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        setLocationState("denied");
        return;
      }
      const position = await getPositionWithTimeout();
      const nextLatitude = Number(position.coords.latitude.toFixed(6));
      const nextLongitude = Number(position.coords.longitude.toFixed(6));
      const nextAccuracy = position.coords.accuracy == null ? undefined : Math.round(position.coords.accuracy);
      setLatitude(String(nextLatitude));
      setLongitude(String(nextLongitude));
      setAccuracy(nextAccuracy == null ? "" : String(nextAccuracy));
      patch({latitude:nextLatitude, longitude:nextLongitude, location_accuracy:nextAccuracy, location_confirmed:false});
      setLocationState("success");
    } catch (locationError) {
      setLocationState(locationError instanceof Error && locationError.message === "LOCATION_TIMEOUT" ? "timeout" : "error");
    }
  }

  function parseOptionalNumber(value: string) {
    if (!value.trim()) return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
  }

  function next() {
    const nextLatitude = parseOptionalNumber(latitude);
    const nextLongitude = parseOptionalNumber(longitude);
    const nextAccuracy = parseOptionalNumber(accuracy);
    const candidate = {...draft, latitude:nextLatitude, longitude:nextLongitude, location_accuracy:nextAccuracy};
    const issue = validateLocationStep(candidate)[0];
    if (issue) {
      setError(issue.message);
      return;
    }
    patch({latitude:nextLatitude, longitude:nextLongitude, location_accuracy:nextAccuracy});
    setError("");
    router.push("/report-media");
  }

  const locationMessage = locationState === "success" ? t("locationSuccess")
    : locationState === "denied" ? t("locationDenied")
      : locationState === "timeout" ? t("locationTimeout")
        : locationState === "error" ? t("locationError") : "";

  return (
    <Screen title={t("locationTitle")} subtitle={t("locationSubtitle")}>
      <Button mode="contained-tonal" icon="crosshairs-gps" loading={locationState === "requesting"} disabled={locationState === "requesting"} onPress={() => void locate()}>
        {locationState === "requesting" ? t("locating") : locationState === "success" ? t("refreshLocation") : t("useLocation")}
      </Button>
      {locationMessage ? <HelperText type={locationState === "success" ? "info" : "error"} visible>{locationMessage}</HelperText> : null}
      <Button mode="outlined" onPress={() => setStateDialog(true)}>{draft.state || `${t("chooseState")} *`}</Button>
      <ChoiceDialog visible={stateDialog} title={t("chooseState")} choices={TARGET_STATES} value={draft.state} onDismiss={() => setStateDialog(false)} onSelect={choice => { patch({state:choice, district:"", location_confirmed:false}); setStateDialog(false); }} />
      <Button mode="outlined" disabled={!selectedState} onPress={() => setDistrictDialog(true)}>{draft.district || `${t("chooseDistrict")} *`}</Button>
      <ChoiceDialog visible={districtDialog} title={t("chooseDistrict")} choices={districts} value={draft.district} onDismiss={() => setDistrictDialog(false)} onSelect={choice => { patch({district:choice, location_confirmed:false}); setDistrictDialog(false); }} />
      <TextInput label={`${t("city")} *`} value={draft.city} onChangeText={value => patch({city:value, location_confirmed:false})} maxLength={120} />
      <TextInput label={t("landmark")} value={draft.landmark} onChangeText={value => patch({landmark:value, location_confirmed:false})} maxLength={160} />
      <TextInput label={t("addressDescription")} value={draft.address_description} onChangeText={value => patch({address_description:value, location_confirmed:false})} multiline numberOfLines={3} maxLength={500} />
      <Text variant="titleSmall" style={styles.manualTitle}>Manual coordinates</Text>
      <TextInput label={t("latitude")} value={latitude} onChangeText={value => { setLatitude(value); update("location_confirmed", false); }} keyboardType="numbers-and-punctuation" />
      <TextInput label={t("longitude")} value={longitude} onChangeText={value => { setLongitude(value); update("location_confirmed", false); }} keyboardType="numbers-and-punctuation" />
      <TextInput label={t("accuracy")} value={accuracy} onChangeText={value => { setAccuracy(value); update("location_confirmed", false); }} keyboardType="decimal-pad" />
      {/* A native map is intentionally omitted until its Expo native module is configured and tested. */}
      <InfoCard title={t("mapUnavailableTitle")}>{t("mapUnavailable")}</InfoCard>
      <Checkbox.Item label={t("confirmLocation")} status={draft.location_confirmed ? "checked" : "unchecked"} onPress={() => update("location_confirmed", !draft.location_confirmed)} />
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      <Button mode="contained" contentStyle={styles.touchTarget} onPress={next}>{t("continuePhotos")}</Button>
    </Screen>
  );
}

const styles = StyleSheet.create({
  dialogArea: {maxHeight:420, paddingHorizontal:0},
  manualTitle: {fontWeight:"800", marginTop:8},
  touchTarget: {minHeight:48},
});
