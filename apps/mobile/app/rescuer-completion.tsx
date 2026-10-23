import * as ImagePicker from "expo-image-picker";
import {useFocusEffect, useLocalSearchParams} from "expo-router";
import {useCallback, useEffect, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Text, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {Booking} from "@spilton/shared-types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

type Picked = {uri:string; name:string; type:string};

export default function RescuerCompletionScreen() {
  const {bookingId} = useLocalSearchParams<{bookingId: string}>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [outcomes, setOutcomes] = useState<Array<{code:string;label:string}>>([]);
  const [outcome, setOutcome] = useState("AUTHORIZED_RESCUE_COMPLETED");
  const [observations, setObservations] = useState("");
  const [actions, setActions] = useState("");
  const [species, setSpecies] = useState("");
  const [image, setImage] = useState<Picked | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!bookingId) return;
    try {setBooking(await api<Booking>("/api/v1/bookings/" + bookingId));}
    catch (reason) {setMessage(reason instanceof Error ? reason.message : "Booking unavailable.");}
  }, [bookingId]);
  useFocusEffect(useCallback(() => {void load();}, [load]));
  useEffect(() => {api<Array<{code:string;label:string}>>("/api/v1/rescue-outcomes").then(setOutcomes).catch(() => setMessage("Outcome directory unavailable."));}, []);

  async function start() {
    if (!bookingId) return;
    setBusy(true);
    try {await api("/api/v1/bookings/" + bookingId + "/rescue/start", {method:"POST"}); await load();}
    catch (reason) {setMessage(reason instanceof Error ? reason.message : "Could not start.");}
    finally {setBusy(false);}
  }
  async function pick() {
    const result = await ImagePicker.launchImageLibraryAsync({mediaTypes:["images"],quality:0.8});
    if (!result.canceled) {
      const asset = result.assets[0];
      setImage({uri:asset.uri,name:asset.fileName || "demo-evidence.jpg",type:asset.mimeType || "image/jpeg"});
    }
  }
  async function complete() {
    if (!bookingId) return;
    setBusy(true);
    try {
      if (image) {
        const body = new FormData();
        body.append("evidence_type", "OUTCOME");
        body.append("file", {uri:image.uri,name:image.name,type:image.type} as unknown as Blob);
        await api("/api/v1/bookings/" + bookingId + "/rescue/evidence", {method:"POST",body,timeoutMs:30_000});
      }
      await api("/api/v1/bookings/" + bookingId + "/complete", {
        method:"POST",
        headers:{"Idempotency-Key":"mobile-completion-" + Date.now()},
        body:JSON.stringify({outcome_code:outcome,observations,authorized_action_summary:actions,species_text:species || null,confirm_demo:true}),
      });
      setMessage("Demo completion saved; location sharing is stopped.");
      await load();
    } catch (reason) {setMessage(reason instanceof Error ? reason.message : "Completion failed.");}
    finally {setBusy(false);}
  }
  return <Screen title="Rescue completion" subtitle="Create a private, factual demo completion record.">
    <View style={styles.warning}><Text style={styles.warningText}>SIMULATION ONLY · NO HANDLING AUTHORITY IS GRANTED</Text></View>
    {!booking ? <Text>{message || "Loading…"}</Text> : <Card><Card.Content style={styles.stack}><Text variant="titleLarge" style={styles.title}>{booking.booking_reference}</Text><Text>Status: {booking.status.replaceAll("_"," ")}</Text>{booking.status === "ARRIVED" ? <Button mode="contained" loading={busy} onPress={() => void start()}>Start demo work record</Button> : null}{booking.status === "IN_PROGRESS" ? <><Text variant="titleMedium">Outcome</Text>{outcomes.map((item) => <Button key={item.code} mode={outcome === item.code ? "contained" : "outlined"} onPress={() => setOutcome(item.code)}>{item.label}</Button>)}<TextInput mode="outlined" label="Observations" multiline value={observations} onChangeText={setObservations}/><TextInput mode="outlined" label="Authorized action summary" multiline value={actions} onChangeText={setActions}/><TextInput mode="outlined" label="Species note (optional, unverified)" value={species} onChangeText={setSpecies}/><Button mode="outlined" onPress={() => void pick()}>{image ? image.name : "Choose optional private image"}</Button><Text style={styles.caption}>Never approach a snake for a photo. JPEG, PNG or WebP only; video is disabled.</Text><Button mode="contained" loading={busy} disabled={observations.trim().length < 5 || actions.trim().length < 5} onPress={() => void complete()}>Submit demo completion</Button></> : null}</Card.Content></Card>}
    {message ? <Text style={styles.message}>{message}</Text> : null}
  </Screen>;
}
const styles=StyleSheet.create({warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center"},stack:{gap:10},title:{fontWeight:"900",color:colors.forest},caption:{fontSize:12,color:"#64748B"},message:{fontWeight:"700",color:"#92400E"}});
