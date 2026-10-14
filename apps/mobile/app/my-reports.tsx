import {Fragment, useCallback, useState} from "react";
import {useFocusEffect, useRouter} from "expo-router";
import {Button, HelperText} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import type {IncidentListItem, Paginated} from "@/features/incidents/types";
import {STATUS_TRANSLATION_KEYS} from "@/features/incidents/status";
import {api, normalizePage} from "@/services/api";
import {localizedError} from "@/services/errors";
import {useI18n} from "@/services/i18n";

const PAGE_SIZE = 20;

export default function MyReports() {
  const router = useRouter();
  const {t} = useI18n();
  const [items, setItems] = useState<IncidentListItem[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (nextPage = 1, append = false) => {
    setLoading(true);
    setError("");
    try {
      const result = normalizePage(await api<Paginated<IncidentListItem> | IncidentListItem[]>(
        `/api/v1/incidents/mine?page=${nextPage}&page_size=${PAGE_SIZE}`,
      ));
      setItems(current => append ? [...current, ...result.items] : result.items);
      setPage(result.page);
      setPages(result.pages);
    } catch (requestError) {
      setError(localizedError(requestError, t));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  return (
    <Screen title={t("myReportsTitle")} subtitle={t("myReportsSubtitle")}>
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      {error ? <Button mode="outlined" onPress={() => void load()}>{t("retry")}</Button> : null}
      {!loading && !error && items.length === 0 ? <InfoCard title={t("noReports")}>{t("demoOnly")}</InfoCard> : null}
      {items.map(incident => (
        <Fragment key={incident.id}>
          <InfoCard title={`${incident.reference_code} · ${t(STATUS_TRANSLATION_KEYS[incident.status])}`}>
            {incident.city}, {incident.district}, {incident.state}{"\n"}
            {new Date(incident.created_at).toLocaleString()}{"\n"}
            {t("demoOnly")}
          </InfoCard>
          <Button compact mode="outlined" onPress={() => router.push(`/incidents/${incident.id}`)}>{t("viewReport")}</Button>
        </Fragment>
      ))}
      {loading ? <Button loading disabled>{t("myReportsTitle")}</Button> : null}
      {!loading && page < pages ? <Button mode="outlined" onPress={() => void load(page + 1, true)}>{t("loadMore")}</Button> : null}
      <Button onPress={() => router.push("/report")}>{t("reportAction")}</Button>
    </Screen>
  );
}
