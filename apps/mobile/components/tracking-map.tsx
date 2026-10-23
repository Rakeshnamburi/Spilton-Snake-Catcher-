import {StyleSheet, View} from "react-native";
import MapView, {Marker, Polyline} from "react-native-maps";
import {Text} from "react-native-paper";
import type {BookingTracking} from "@/features/marketplace/types";
import {colors} from "@/services/theme";

export function TrackingMap({tracking}:{tracking:BookingTracking}){
 const point=tracking.latest_location;
 const latitude=point?.latitude??tracking.destination_latitude;
 const longitude=point?.longitude??tracking.destination_longitude;
 if(latitude==null||longitude==null)return <View style={styles.empty}><Text style={styles.emptyTitle}>Map unavailable</Text><Text>No authorized simulated coordinates have been shared.</Text></View>;
 const route=tracking.route.coordinates.map(([lng,lat])=>({latitude:lat,longitude:lng}));
 return <View style={styles.container}><MapView style={styles.map} initialRegion={{latitude,longitude,latitudeDelta:0.06,longitudeDelta:0.06}}><Marker coordinate={{latitude,longitude}} pinColor={colors.emerald} title="Last simulated rescuer point"/>{tracking.destination_latitude!=null&&tracking.destination_longitude!=null?<Marker coordinate={{latitude:tracking.destination_latitude,longitude:tracking.destination_longitude}} pinColor={colors.danger} title="Customer destination"/>:null}{route.length>1?<Polyline coordinates={route} strokeColor={colors.forest} strokeWidth={5}/>:null}</MapView><Text style={styles.legend}>Green: last simulated point · Red: destination</Text></View>;
}
const styles=StyleSheet.create({container:{borderRadius:16,overflow:"hidden",backgroundColor:"white"},map:{height:340,width:"100%"},legend:{padding:12,fontSize:12,fontWeight:"700",color:"#475569"},empty:{padding:24,borderRadius:16,backgroundColor:"#FEF3C7",gap:6},emptyTitle:{fontWeight:"900",color:"#92400E"}});
