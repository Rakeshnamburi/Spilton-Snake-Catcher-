import {Href, useFocusEffect, useLocalSearchParams, useRouter} from "expo-router";
import {useCallback, useState} from "react";
import {Alert, StyleSheet, View} from "react-native";
import {Button, Card, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {BookingChatPanel, MaskedCallPanel} from "@/features/marketplace/booking-extras";
import type {Booking} from "@/features/marketplace/types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

export default function BookingDetailsScreen() {
  const {id} = useLocalSearchParams<{id:string}>();
  const router = useRouter();
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
      <View style={styles.warning}><Text style={styles.warningText}>DEMO BOOKING · ₹0 COLLECTED · SIMULATED TRACKING ONLY</Text></View>
      <Card><Card.Content style={styles.stack}><Text variant="headlineSmall" style={styles.title}>{booking.booking_reference}</Text><Text variant="titleMedium">{booking.status.replaceAll("_", " ")}</Text><Text>{booking.rescuer_display_name} · {booking.organization}</Text>{booking.status === "ARRIVED" ? <Text style={styles.arrival}>The fictional demo rescuer marked the location as reached. GPS does not prove arrival.</Text> : null}{booking.arrival_review_warning ? <Text style={styles.caution}>Arrival differed significantly from the approved location. Review before confirming.</Text> : null}<Text>Submitted {new Date(booking.created_at).toLocaleString()}</Text><Text>Location: {booking.manual_address || `${booking.latitude ?? "—"}, ${booking.longitude ?? "—"}`}</Text><Text style={styles.body}>{booking.customer_notes}</Text>{["ACCEPTED","EN_ROUTE","ARRIVED"].includes(booking.status)?<Button mode="contained" icon="map-marker-path" onPress={()=>router.push(`/bookings/${booking.id}/tracking`)}>Open demo tracking</Button>:null}{["REQUESTED","PENDING_RESCUER_RESPONSE","ACCEPTED","EN_ROUTE","ARRIVED"].includes(booking.status) ? <Button mode="outlined" textColor={colors.danger} loading={busy} disabled={busy} onPress={confirmCancel}>Cancel simulation</Button> : null}</Card.Content></Card>
      <Card><Card.Content style={styles.stack}><Text variant="titleLarge" style={styles.title}>Status timeline</Text>{booking.history.map(item => <View style={styles.timeline} key={item.id}><Text style={styles.timelineTitle}>{item.status.replaceAll("_", " ")}</Text><Text style={styles.caption}>{new Date(item.created_at).toLocaleString()}</Text>{item.note ? <Text>{item.note}</Text> : null}</View>)}</Card.Content></Card>
      <MaskedCallPanel bookingId={booking.id}/>
      <BookingChatPanel bookingId={booking.id}/>
      {["COMPLETED","UNABLE_TO_ASSIST","DISPUTED"].includes(booking.status) ? <Button mode="contained" icon="check-decagram" onPress={()=>router.push({pathname:"/booking-completion",params:{bookingId:booking.id}} as unknown as Href)}>Open completion, receipt & review</Button> : null}
      <Text style={styles.caption}>Exact customer location remains protected. Foreground demo tracking requires rescuer consent and never starts in the background.</Text>
    </>}
  </Screen>;
}

const styles=StyleSheet.create({error:{color:colors.danger,fontWeight:"700"},warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center"},stack:{gap:10},title:{fontWeight:"900",color:colors.forest},body:{lineHeight:21,color:"#475569"},arrival:{backgroundColor:"#DCFCE7",color:colors.forest,padding:10,borderRadius:8,fontWeight:"700"},caution:{backgroundColor:"#FEF3C7",color:"#92400E",padding:10,borderRadius:8,fontWeight:"700"},timeline:{borderLeftWidth:2,borderLeftColor:colors.emerald,paddingLeft:12,paddingVertical:4},timelineTitle:{fontWeight:"800"},caption:{fontSize:12,color:"#64748B"}});
