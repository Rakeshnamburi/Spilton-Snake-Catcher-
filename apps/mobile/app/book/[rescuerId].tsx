import {useLocalSearchParams, useRouter} from "expo-router";
import {useEffect, useRef, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Checkbox, Switch, Text, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {useMarketplace} from "@/features/marketplace/context";
import type {Booking, PublicRescuer} from "@/features/marketplace/types";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";

export default function BookingRequestScreen() {
  const {rescuerId} = useLocalSearchParams<{rescuerId:string}>();
  const router = useRouter();
  const {location, selectedRescuer, setSelectedRescuer, setLastBooking} = useMarketplace();
  const [rescuer, setRescuer] = useState<PublicRescuer | null>(selectedRescuer?.id === rescuerId ? selectedRescuer : null);
  const [notes, setNotes] = useState("");
  const [injury, setInjury] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [review, setReview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const idempotencyKey = useRef(`mobile-booking-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  useEffect(() => { if (!rescuerId) return; api<PublicRescuer>(`/api/v1/rescuers/${encodeURIComponent(rescuerId)}`).then(value => {setRescuer(value); setSelectedRescuer(value);}).catch(reason => setError(reason instanceof Error ? reason.message : "Profile unavailable.")); }, [rescuerId, setSelectedRescuer]);

  function validate() {
    if (!location.state_code || !location.district_code) return setError("Select an imported LGD state and district first.");
    if (!location.manualAddress && (location.latitude === undefined || location.longitude === undefined)) return setError("Enter a manual address or capture coordinates.");
    if (notes.trim().length < 10) return setError("Describe the situation in at least 10 characters.");
    if (!confirmed) return setError("Confirm the demo and safety acknowledgement.");
    setError("");
    setReview(true);
  }

  async function submit() {
    if (!rescuer || busy) return;
    setBusy(true);
    setError("");
    try {
      const booking = await api<Booking>("/api/v1/bookings", {method:"POST",headers:{"Idempotency-Key":idempotencyKey.current},body:JSON.stringify({rescuer_id:rescuer.id,state_code:location.state_code,district_code:location.district_code,subdistrict_code:location.subdistrict_code || undefined,village_code:location.village_code || undefined,manual_address:location.manualAddress || undefined,landmark:location.landmark || undefined,latitude:location.latitude,longitude:location.longitude,location_accuracy:location.accuracy,customer_notes:injury ? `[Injury reported — 112 guidance shown] ${notes.trim()}` : notes.trim(),confirm_demo_and_safety:true})});
      setLastBooking(booking);
      router.replace({pathname:"/booking-confirmation",params:{id:booking.id}});
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401 ? "Your session expired. Sign in and try again." : reason instanceof ApiError && reason.code === "IDEMPOTENCY_CONFLICT" ? "This submission changed after it was sent. Start a new request." : reason instanceof Error ? reason.message : "Request failed.");
    } finally { setBusy(false); }
  }

  if (review && rescuer) return <Screen title="Review demo request" subtitle="Nothing is sent until you press the final simulated submit button.">
    <View style={styles.danger}><Text style={styles.dangerText}>NO LIVE DISPATCH OR PAYMENT</Text></View>
    <Card><Card.Content style={styles.stack}><Text variant="titleLarge" style={styles.title}>{rescuer.display_name}</Text><Text>{rescuer.organization}</Text><Text>LGD {location.state_code} / {location.district_code}</Text><Text>{location.manualAddress || `${location.latitude}, ${location.longitude}`}</Text><Text style={styles.body}>{notes}</Text><Text style={styles.money}>₹0.00 collected. 10% commission concept is illustrative only.</Text></Card.Content></Card>
    <View style={styles.row}><Button style={styles.flex} mode="outlined" onPress={() => setReview(false)}>Edit</Button><Button style={styles.flex} mode="contained" loading={busy} disabled={busy} onPress={() => void submit()}>Submit demo</Button></View>
    {error ? <Text style={styles.error}>{error}</Text> : null}
  </Screen>;

  return <Screen title="Request demo assistance" subtitle="Create a simulated request to a fictional eligible profile. No real message is sent.">
    {injury ? <View style={styles.emergency}><Text variant="titleMedium" style={styles.emergencyTitle}>Call 112 and seek immediate medical care now</Text><Text>Do not wait for this demo form. Submission is not emergency assistance.</Text></View> : null}
    {rescuer ? <Card><Card.Content><Text variant="titleLarge" style={styles.title}>{rescuer.display_name}</Text><Text>{rescuer.organization} · {rescuer.availability} demo status</Text></Card.Content></Card> : <Text>Loading profile…</Text>}
    <Button mode="outlined" icon="map-marker" onPress={() => router.push("/marketplace-location")}>{location.state_code ? `LGD ${location.state_code} / ${location.district_code || "district needed"}` : "Select GPS or manual location"}</Button>
    <View style={styles.switchRow}><View style={styles.flex}><Text variant="titleSmall">Is anyone bitten or injured?</Text><Text style={styles.caption}>This only displays urgent medical guidance.</Text></View><Switch value={injury} onValueChange={setInjury}/></View>
    <TextInput mode="outlined" label="Situation details" multiline numberOfLines={5} value={notes} onChangeText={setNotes}/>
    <View style={styles.checkRow}><Checkbox status={confirmed ? "checked" : "unchecked"} onPress={() => setConfirmed(value => !value)}/><Text style={styles.checkText} onPress={() => setConfirmed(value => !value)}>I understand this is a simulation, no rescuer is contacted, no payment is collected, and I must use 112 for a medical emergency.</Text></View>
    {error ? <Text style={styles.error}>{error}</Text> : null}
    <Button mode="contained" onPress={validate}>Review simulated request</Button>
  </Screen>;
}

const styles=StyleSheet.create({danger:{backgroundColor:colors.danger,borderRadius:12,padding:14},dangerText:{color:"white",fontWeight:"900",textAlign:"center"},emergency:{backgroundColor:"#FEF2F2",borderWidth:2,borderColor:colors.danger,borderRadius:12,padding:16,gap:6},emergencyTitle:{fontWeight:"900",color:colors.danger},title:{fontWeight:"900",color:colors.forest},stack:{gap:10},body:{lineHeight:21},money:{fontWeight:"800",color:colors.forest},row:{flexDirection:"row",gap:10},flex:{flex:1},switchRow:{flexDirection:"row",alignItems:"center",gap:12},caption:{fontSize:12,color:"#64748B"},checkRow:{flexDirection:"row",alignItems:"flex-start"},checkText:{flex:1,fontSize:13,lineHeight:19,paddingTop:8},error:{color:colors.danger,fontWeight:"700"}});
