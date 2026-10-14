import {useFocusEffect} from "expo-router";
import {useCallback, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Chip, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {Booking, MarketplacePage} from "@/features/marketplace/types";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";

export default function RescuerBookingsScreen(){
 const [data,setData]=useState<MarketplacePage<Booking>|null>(null);const[error,setError]=useState("");const[busy,setBusy]=useState("");
 const load=useCallback(async()=>{try{setData(await api<MarketplacePage<Booking>>("/api/v1/bookings/assigned"));setError("");}catch(reason){setError(reason instanceof ApiError&&reason.status===403?"A verified RESCUER account is required.":reason instanceof Error?reason.message:"Unable to load requests.");}},[]);
 useFocusEffect(useCallback(()=>{void load();},[load]));
 async function respond(item:Booking,action:"accept"|"reject"){setBusy(item.id);try{await api(`/api/v1/bookings/${item.id}/${action}`,{method:"POST",body:JSON.stringify({note:`Simulated ${action} from mobile.`})});await load();}catch(reason){setError(reason instanceof ApiError&&reason.status===409?"This request already changed. The list was refreshed.":reason instanceof Error?reason.message:"Response failed.");await load();}finally{setBusy("");}}
 return <Screen title="Incoming demo requests" subtitle="Only requests assigned to this verified profile can be accepted or rejected."><View style={styles.warning}><Text style={styles.warningText}>SIMULATED ACTIONS ONLY · EXACT CUSTOMER LOCATION HIDDEN</Text></View>{error?<Text style={styles.error}>{error}</Text>:null}{data?.items.length===0?<Text>No assigned demo requests.</Text>:null}{data?.items.map(item=><Card key={item.id}><Card.Content style={styles.stack}><Chip>{item.status.replaceAll("_"," ")}</Chip><Text variant="titleLarge" style={styles.title}>{item.booking_reference}</Text><Text>Approximate: {item.latitude??"manual"}, {item.longitude??"location"}</Text><Text>LGD {item.state_code} / {item.district_code}</Text><Text style={styles.body}>{item.customer_notes}</Text>{item.status==="PENDING_RESCUER_RESPONSE"?<View style={styles.row}><Button style={styles.flex} mode="contained" loading={busy===item.id} disabled={!!busy} onPress={()=>void respond(item,"accept")}>Accept demo</Button><Button style={styles.flex} mode="outlined" disabled={!!busy} onPress={()=>void respond(item,"reject")}>Reject</Button></View>:null}</Card.Content></Card>)}</Screen>;
}
const styles=StyleSheet.create({warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center",fontSize:12},error:{color:colors.danger,fontWeight:"700"},stack:{gap:9},title:{fontWeight:"900",color:colors.forest},body:{lineHeight:20,color:"#475569"},row:{flexDirection:"row",gap:8},flex:{flex:1}});
