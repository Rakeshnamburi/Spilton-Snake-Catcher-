import {useEffect} from "react";
import {useRouter} from "expo-router";
import {StyleSheet,View} from "react-native";
import {ActivityIndicator,Text} from "react-native-paper";
import {colors} from "@/services/theme";
export default function Splash(){const router=useRouter();useEffect(()=>{const timer=setTimeout(()=>router.replace("/onboarding"),900);return()=>clearTimeout(timer)},[router]);return <View style={styles.container}><View style={styles.mark}><Text style={styles.markText}>S</Text></View><Text variant="headlineMedium" style={styles.title}>SPILTON</Text><Text style={styles.tagline}>Saving Lives. Protecting Wildlife.</Text><ActivityIndicator color="white" style={{marginTop:32}}/></View>}
const styles=StyleSheet.create({container:{flex:1,alignItems:"center",justifyContent:"center",backgroundColor:colors.forest},mark:{width:82,height:82,borderRadius:24,backgroundColor:"white",alignItems:"center",justifyContent:"center"},markText:{fontSize:42,fontWeight:"900",color:colors.forest},title:{color:"white",fontWeight:"900",marginTop:18},tagline:{color:"#bbf7d0",marginTop:7}});

