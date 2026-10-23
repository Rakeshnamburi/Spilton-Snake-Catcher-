import {useFocusEffect, useRouter} from "expo-router";
import {useCallback, useState} from "react";
import {StyleSheet} from "react-native";
import {Button, Card, Chip, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {Booking, MarketplacePage} from "@/features/marketplace/types";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";
import {useI18n} from "@/services/i18n";

export default function MyBookingsScreen() {
  const router = useRouter();
  const {t} = useI18n();
  const [data, setData] = useState<MarketplacePage<Booking> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await api<MarketplacePage<Booking>>("/api/v1/bookings/mine")); setError(""); }
    catch (reason) { setError(reason instanceof ApiError && reason.status === 401 ? "Sign in to view protected demo bookings." : reason instanceof Error ? reason.message : "Unable to load bookings."); }
    finally { setLoading(false); }
  }, []);
  useFocusEffect(useCallback(() => { void load(); }, [load]));
  return <Screen title="My demo bookings" subtitle="Reference numbers alone never grant access; these records require your authenticated session.">
    {loading ? <Text>{t("bookingLoading")}</Text> : null}
    {error ? <Text style={styles.error}>{error}</Text> : null}
    {!loading && data?.items.length === 0 ? <Card><Card.Content><Text variant="titleMedium" style={styles.title}>{t("bookingNone")}</Text><Button onPress={() => router.push("/nearby-rescuers")}>{t("bookingBrowse")}</Button></Card.Content></Card> : null}
    {data?.items.map(booking => <Card key={booking.id}><Card.Content style={styles.stack}><Chip compact>{booking.status.replaceAll("_", " ")}</Chip><Text variant="titleLarge" style={styles.title}>{booking.booking_reference}</Text><Text>{booking.rescuer_display_name}</Text><Text>{new Date(booking.created_at).toLocaleString()}</Text><Text style={styles.demo}>DEMO ONLY · payment {booking.payment_status.toLowerCase()}</Text><Button mode="outlined" onPress={() => router.push({pathname:"/bookings/[id]",params:{id:booking.id}})}>{t("bookingView")}</Button></Card.Content></Card>)}
  </Screen>;
}

const styles=StyleSheet.create({error:{color:colors.danger,fontWeight:"700"},title:{fontWeight:"900",color:colors.forest},stack:{gap:9},demo:{fontWeight:"800",color:colors.danger}});
