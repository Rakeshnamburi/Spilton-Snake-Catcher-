import {useFocusEffect, useLocalSearchParams} from "expo-router";
import {useCallback, useState} from "react";
import {Alert, StyleSheet, View} from "react-native";
import {Button, Card, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {Booking} from "@/features/marketplace/types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

export default function BookingDetailsScreen() {
  const {id} = useLocalSearchParams<{id:string}>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    try { setBooking(await api<Booking>(`/api/v1/bookings/${encodeURIComponent(id)}`)); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Booking unavailable."); }
  }, [id]);
  useFocusEffect(useCallback(() => { void load(); }, [load]));

  function confirmCancel() {
    Alert.alert("Cancel simulated booking?", "This changes only the demo record.", [{text:"Keep",style:"cancel"},{text:"Cancel demo",style:"destructive",onPress:() => void cancel()}]);
  }
  async function cancel() {
    if (!booking) return;
    setBusy(true);
    try { setBooking(await api<Booking>(`/api/v1/bookings/${booking.id}/cancel`, {method:"POST",body:JSON.stringify({note:"Cancelled by customer from mobile."})})); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Cancellation failed."); }
    finally { setBusy(false); }
  }
  return <Screen title="Demo booking details" subtitle="No status shown here represents a live dispatch.">
    {error ? <Text style={styles.error}>{error}</Text> : null}
    {!booking ? <Text>Loading protected status…</Text> : <>
      <View style={styles.warning}><Text style={styles.warningText}>DEMO BOOKING · ₹0 COLLECTED · NO LIVE TRACKING</Text></View>
      <Card><Card.Content style={styles.stack}><Text variant="headlineSmall" style={styles.title}>{booking.booking_reference}</Text><Text variant="titleMedium">{booking.status.replaceAll("_", " ")}</Text><Text>{booking.rescuer_display_name} · {booking.organization}</Text><Text>Submitted {new Date(booking.created_at).toLocaleString()}</Text><Text>Location: {booking.manual_address || `${booking.latitude ?? "—"}, ${booking.longitude ?? "—"}`}</Text><Text style={styles.body}>{booking.customer_notes}</Text>{["REQUESTED","PENDING_RESCUER_RESPONSE","ACCEPTED"].includes(booking.status) ? <Button mode="outlined" textColor={colors.danger} loading={busy} disabled={busy} onPress={confirmCancel}>Cancel simulation</Button> : null}</Card.Content></Card>
      <Card><Card.Content style={styles.stack}><Text variant="titleLarge" style={styles.title}>Status timeline</Text>{booking.history.map(item => <View style={styles.timeline} key={item.id}><Text style={styles.timelineTitle}>{item.status.replaceAll("_", " ")}</Text><Text style={styles.caption}>{new Date(item.created_at).toLocaleString()}</Text>{item.note ? <Text>{item.note}</Text> : null}</View>)}</Card.Content></Card>
      <Text style={styles.caption}>Exact customer location remains protected. Day 3 gives assigned demo rescuers only approximate coordinates and never starts background tracking.</Text>
    </>}
  </Screen>;
}

const styles=StyleSheet.create({error:{color:colors.danger,fontWeight:"700"},warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center"},stack:{gap:10},title:{fontWeight:"900",color:colors.forest},body:{lineHeight:21,color:"#475569"},timeline:{borderLeftWidth:2,borderLeftColor:colors.emerald,paddingLeft:12,paddingVertical:4},timelineTitle:{fontWeight:"800"},caption:{fontSize:12,color:"#64748B"}});
