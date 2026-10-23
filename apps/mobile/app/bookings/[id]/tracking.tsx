import {useFocusEffect, useLocalSearchParams, useRouter} from "expo-router";
import {useCallback, useEffect, useMemo, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Chip, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {TrackingMap} from "@/components/tracking-map";
import type {Booking, BookingTracking} from "@/features/marketplace/types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

export default function LiveBookingTrackingScreen(){
 const{id}=useLocalSearchParams<{id:string}>();const router=useRouter();
 const[booking,setBooking]=useState<Booking|null>(null);const[tracking,setTracking]=useState<BookingTracking|null>(null);const[error,setError]=useState("");const[connection,setConnection]=useState("CONNECTING");
 const load=useCallback(async()=>{if(!id)return;try{const[b,t]=await Promise.all([api<Booking>(`/api/v1/bookings/${id}`),api<BookingTracking>(`/api/v1/bookings/${id}/tracking`)]);setBooking(b);setTracking(t);setConnection("POLLING ACTIVE");setError("");}catch(reason){setConnection("OFFLINE");setError(reason instanceof Error?reason.message:"Tracking unavailable.");}},[id]);
 useFocusEffect(useCallback(()=>{void load();},[load]));
 useEffect(()=>{const timer=setInterval(()=>void load(),7000);return()=>clearInterval(timer)},[load]);
 const stale=useMemo(()=>!tracking?.last_location_at||Date.now()-new Date(tracking.last_location_at).getTime()>30000,[tracking?.last_location_at]);
 return <Screen title="Simulated live tracking" subtitle="Private polling fallback keeps status current when a real-time stream is unavailable.">
  <View style={styles.warning}><Text style={styles.warningText}>DEMO MOVEMENT ONLY · NOT AN ACTIVE RESCUE SERVICE · SNAKEBITE: CALL 112</Text></View>
  {error?<Text style={styles.error}>{error}</Text>:null}
  {!booking||!tracking?<Text>Loading protected tracking…</Text>:<>
   <Card><Card.Content style={styles.stack}><Chip>{booking.status.replaceAll("_"," ")}</Chip><Text variant="titleLarge" style={styles.title}>{booking.booking_reference}</Text><Text>{booking.rescuer_display_name} · verified demo profile</Text><Text>Connection: {connection}</Text></Card.Content></Card>
   {stale?<Card style={styles.stale}><Card.Content><Text style={styles.staleTitle}>Not live right now</Text><Text>{tracking.last_location_at?`Last simulated point: ${new Date(tracking.last_location_at).toLocaleString()}`:"No simulated point has been shared."}</Text></Card.Content></Card>:null}
   <TrackingMap tracking={tracking}/>
   <Card><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>Journey status</Text><Text>Tracking: {tracking.status?.replaceAll("_"," ")??"NOT STARTED"}</Text><Text>Last GPS: {tracking.last_location_at?new Date(tracking.last_location_at).toLocaleString():"Unavailable"}</Text><Text>ETA: {tracking.route.eta_at?new Date(tracking.route.eta_at).toLocaleString():"Unavailable"}</Text><Text style={styles.caption}>{tracking.route.message}</Text>{tracking.route.road_distance_km!=null?<Text>Road estimate: {tracking.route.road_distance_km} km</Text>:tracking.route.geographic_distance_km!=null?<Text>Geographic distance only: {tracking.route.geographic_distance_km} km</Text>:null}</Card.Content></Card>
   <View style={styles.row}><Button style={styles.flex} mode="contained" onPress={()=>void load()}>Refresh</Button><Button style={styles.flex} mode="outlined" onPress={()=>router.push(`/bookings/${booking.id}`)}>Timeline</Button></View>
  </>}
 </Screen>;
}
const styles=StyleSheet.create({warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center",fontSize:12},error:{color:colors.danger,fontWeight:"700"},stack:{gap:8},title:{fontWeight:"900",color:colors.forest},stale:{backgroundColor:"#FEF3C7"},staleTitle:{fontWeight:"900",color:"#92400E",marginBottom:5},caption:{fontSize:12,lineHeight:18,color:"#475569"},row:{flexDirection:"row",gap:8},flex:{flex:1}});
