import {useCallback, useState} from "react";
import {Alert, Image, StyleSheet, View} from "react-native";
import {useFocusEffect, useLocalSearchParams, useRouter} from "expo-router";
import {Button, Chip, HelperText, Text} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {CANCELLABLE_STATUSES, STATUS_TRANSLATION_KEYS} from "@/features/incidents/status";
import type {Incident} from "@/features/incidents/types";
import {api, getAccessToken, resolveApiUrl} from "@/services/api";
import {localizedError} from "@/services/errors";
import {useI18n} from "@/services/i18n";

export default function IncidentDetails() {
  const {id} = useLocalSearchParams<{id: string}>();
  const router = useRouter();
  const {t} = useI18n();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const [saved, accessToken] = await Promise.all([
        api<Incident>(`/api/v1/incidents/${id}`),
        getAccessToken(),
      ]);
      setIncident(saved);
      setToken(accessToken);
    } catch (requestError) {
      setError(localizedError(requestError, t));
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  async function cancelIncident() {
    if (!incident) return;
    setCancelling(true);
    setError("");
    try {
      setIncident(await api<Incident>(`/api/v1/incidents/${incident.id}/cancel`, {method: "POST"}));
    } catch (requestError) {
      setError(localizedError(requestError, t));
    } finally {
      setCancelling(false);
    }
  }

  function confirmCancellation() {
    Alert.alert(t("cancelConfirmTitle"), t("cancelConfirmBody"), [
      {text: t("keepReport"), style: "cancel"},
      {text: t("cancel"), style: "destructive", onPress: () => void cancelIncident()},
    ]);
  }

  return (
    <Screen title={incident?.reference_code ?? t("navIncident")} subtitle="Private details are visible only to the report owner and authorized demo coordinators.">
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      {error ? <Button mode="outlined" onPress={() => void load()}>{t("retry")}</Button> : null}
      {loading ? <Button loading disabled>{t("navIncident")}</Button> : null}
      {incident ? (
        <>
          <View style={styles.chips}>
            <Chip icon="shield-check">{t(STATUS_TRANSLATION_KEYS[incident.status])}</Chip>
            <Chip icon="flask">{t("demoOnly")}</Chip>
          </View>
          {incident.injury_reported ? <InfoCard title={t("medicalTitle")} danger>{t("medicalGuidance")}</InfoCard> : null}
          <InfoCard title={t("details")}>
            {new Date(incident.sighting_at).toLocaleString()}{"\n"}
            {incident.description}{"\n"}
            Snake visible: {incident.snake_visible ? "Yes" : "No"}{"\n"}
            Immediate danger: {incident.immediate_danger ? "Yes" : "No"}
          </InfoCard>
          <InfoCard title={t("location")}>
            {[incident.city, incident.district, incident.state, incident.landmark].filter(Boolean).join(", ")}
            {incident.address_description ? `\n${incident.address_description}` : ""}
            {incident.latitude == null ? "\nNo GPS coordinates submitted." : `\n${incident.latitude}, ${incident.longitude} · ±${incident.location_accuracy ?? "?"} m`}
          </InfoCard>
          <Text variant="titleMedium" style={styles.sectionTitle}>{t("media")}</Text>
          {!incident.media?.length ? <InfoCard title={t("noMedia")}>{t("photoSafety")}</InfoCard> : null}
          {incident.media?.map((media, index) => (
            <Image
              key={media.id}
              source={{
                uri: resolveApiUrl(media.download_url),
                // Never forward the bearer token to an absolute third-party URL.
                headers: token && !/^https?:\/\//i.test(media.download_url)
                  ? {Authorization: `Bearer ${token}`}
                  : undefined,
              }}
              style={styles.image}
              resizeMode="cover"
              accessibilityLabel={`Authorized incident photo ${index + 1}`}
            />
          ))}
          <Button mode="outlined" icon="timeline-clock" onPress={() => router.push(`/incidents/${incident.id}/timeline`)}>{t("timeline")}</Button>
          {CANCELLABLE_STATUSES.includes(incident.status) ? (
            <Button mode="outlined" textColor="#DC2626" loading={cancelling} disabled={cancelling} onPress={confirmCancellation}>{t("cancelReport")}</Button>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  chips: {flexDirection: "row", flexWrap: "wrap", gap: 8},
  sectionTitle: {color: "#14532D", fontWeight: "800"},
  image: {backgroundColor: "#e2e8f0", borderRadius: 16, height: 240, width: "100%"},
});
