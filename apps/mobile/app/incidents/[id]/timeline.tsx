import {useCallback, useState} from "react";
import {useFocusEffect, useLocalSearchParams} from "expo-router";
import {Button, HelperText, Text} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import type {IncidentEvent} from "@/features/incidents/types";
import {api} from "@/services/api";
import {localizedError} from "@/services/errors";
import {useI18n} from "@/services/i18n";

export default function IncidentTimeline() {
  const {id} = useLocalSearchParams<{id: string}>();
  const {t} = useI18n();
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      setEvents(await api<IncidentEvent[]>(`/api/v1/incidents/${id}/events`));
    } catch (requestError) {
      setError(localizedError(requestError, t));
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  return (
    <Screen title={t("timeline")} subtitle="Every demo workflow change is recorded by the shared backend.">
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      {error ? <Button mode="outlined" onPress={() => void load()}>{t("retry")}</Button> : null}
      {loading ? <Button loading disabled>{t("timeline")}</Button> : null}
      {!loading && !error && events.length === 0 ? <InfoCard title="No events">No incident events are available.</InfoCard> : null}
      {events.map((event, index) => (
        <InfoCard key={event.id} title={`${index + 1}. ${event.event_type.replaceAll("_", " ")}`}>
          {event.details}{"\n"}
          <Text variant="bodySmall">{new Date(event.created_at).toLocaleString()}</Text>
        </InfoCard>
      ))}
    </Screen>
  );
}
