import {useFocusEffect, useRouter} from "expo-router";
import {useCallback, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Chip, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {AvailabilityStatus} from "@/features/marketplace/types";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";

type Profile={id:string;public_display_name:string|null;organization_name:string|null;verification_status:string;availability:AvailabilityStatus;service_area_description:string;authorization_expiry:string|null};
type Notice={id:string;title:string;body:string};
export default function RescuerDashboardScreen() {
  const router=useRouter();
  const [profile,setProfile]=useState<Profile|null>(null);
  const [notices,setNotices]=useState<Notice[]>([]);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const load=useCallback(async()=>{try{const [value,inbox]=await Promise.all([api<Profile>("/api/v1/rescuers/me"),api<Notice[]>("/api/v1/notifications/mine?limit=10").catch(()=>[])]);setProfile(value);setNotices(inbox);setError("");}catch(reason){setError(reason instanceof ApiError&&reason.status===404?"No rescuer application exists.":reason instanceof Error?reason.message:"Dashboard unavailable.");}},[]);
  useFocusEffect(useCallback(()=>{void load();},[load]));
  async function update(status:AvailabilityStatus){setBusy(true);try{setProfile(await api<Profile>("/api/v1/rescuers/me/availability",{method:"PATCH",body:JSON.stringify({status})}));setError("");}catch(reason){setError(reason instanceof Error?reason.message:"Update failed.");}finally{setBusy(false);}}
  return <Screen title="Rescuer dashboard" subtitle="Availability and requests are simulated. They do not permit real wildlife handling.">
    <View style={styles.warning}><Text style={styles.warningText}>DEMO WORKSPACE — NO LIVE DISPATCH</Text></View>
    {!profile&&!error?<Text>Loading protected profile…</Text>:null}
    {error?<Card><Card.Content><Text style={styles.error}>{error}</Text><Button onPress={()=>router.push("/rescuer-register")}>Start onboarding</Button></Card.Content></Card>:null}
    {profile?<><Card><Card.Content style={styles.stack}><Chip>{profile.verification_status.replaceAll("_"," ")}</Chip><Text variant="titleLarge" style={styles.title}>{profile.public_display_name||"Rescuer applicant"}</Text><Text>{profile.organization_name}</Text><Text>{profile.service_area_description}</Text><Text>Availability: {profile.availability} (demo)</Text></Card.Content></Card><View style={styles.row}>{(["AVAILABLE","BUSY","OFFLINE"] as AvailabilityStatus[]).map(status=><Button key={status} style={styles.flex} compact mode={profile.availability===status?"contained":"outlined"} disabled={busy||profile.verification_status!=="VERIFIED"||profile.availability===status} onPress={()=>void update(status)}>{status}</Button>)}</View><Button mode="contained" onPress={()=>router.push("/rescuer-bookings")}>Incoming demo requests</Button></>:null}
    <Card><Card.Content style={styles.stack}><Text variant="titleLarge" style={styles.title}>In-app demo notifications</Text>{notices.length?notices.map(item=><View key={item.id}><Text style={styles.noticeTitle}>{item.title}</Text><Text>{item.body}</Text></View>):<Text>No in-app demo notifications.</Text>}</Card.Content></Card>
  </Screen>;
}
const styles=StyleSheet.create({warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center"},error:{color:colors.danger,fontWeight:"700"},stack:{gap:9},title:{fontWeight:"900",color:colors.forest},row:{flexDirection:"row",gap:6},flex:{flex:1},noticeTitle:{fontWeight:"800",marginTop:8}});
