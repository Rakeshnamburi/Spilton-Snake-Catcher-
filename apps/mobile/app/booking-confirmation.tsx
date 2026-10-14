import {useLocalSearchParams, useRouter} from "expo-router";
import {StyleSheet, View} from "react-native";
import {Button, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {useMarketplace} from "@/features/marketplace/context";
import {colors} from "@/services/theme";

export default function BookingConfirmationScreen() {
  const {id} = useLocalSearchParams<{id:string}>();
  const router = useRouter();
  const {lastBooking} = useMarketplace();
  return <Screen title="Demo booking created" subtitle="The simulated request was stored safely. No real rescue team was notified.">
    <View style={styles.success}><Text variant="headlineSmall" style={styles.title}>Simulation confirmed</Text><Text style={styles.body}>Reference: {lastBooking?.booking_reference ?? id ?? "Saved booking"}</Text><Text style={styles.body}>Status: {lastBooking?.status ?? "PENDING_RESCUER_RESPONSE"}</Text></View>
    <View style={styles.warning}><Text style={styles.warningText}>This is not an emergency response confirmation. For suspected snakebite, call 112 and seek immediate medical care.</Text></View>
    <Button mode="contained" onPress={() => router.replace({pathname:"/bookings/[id]",params:{id:id ?? lastBooking?.id ?? ""}})}>View protected status</Button>
    <Button mode="outlined" onPress={() => router.replace("/home")}>Return home</Button>
  </Screen>;
}
const styles=StyleSheet.create({success:{backgroundColor:"#F0FDF4",borderRadius:16,padding:20,gap:8},title:{fontWeight:"900",color:colors.forest},body:{color:"#166534"},warning:{backgroundColor:"#FEF2F2",borderRadius:12,padding:15},warningText:{color:colors.danger,fontWeight:"800",lineHeight:20}});
