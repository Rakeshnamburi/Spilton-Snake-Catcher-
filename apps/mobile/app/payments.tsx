import {useFocusEffect} from "expo-router";
import {useCallback, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Card, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {DemoPayment} from "@spilton/shared-types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

export default function PaymentsScreen(){
  const[items,setItems]=useState<DemoPayment[]>([]);const[message,setMessage]=useState("");
  useFocusEffect(useCallback(()=>{api<DemoPayment[]>("/api/v1/payments").then(setItems).catch((reason)=>setMessage(reason instanceof Error?reason.message:"Payments unavailable."));},[]));
  return <Screen title="Demo payments" subtitle="Illustrative financial records only; no real money is processed."><View style={styles.warning}><Text style={styles.warningText}>NO REAL CHARGE · NO PAYOUT · NOT TAX INVOICES</Text></View>{items.length?items.map((item)=><Card key={item.id}><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>{item.payment_reference}</Text><Text>{item.method.replaceAll("_"," ")} · {item.status.replaceAll("_"," ")}</Text><Text>₹{item.amount} INR</Text><Text>Commission: {item.commission_amount?"₹"+item.commission_amount:"not applicable"}</Text><Text style={styles.caption}>{new Date(item.created_at).toLocaleString()}</Text></Card.Content></Card>):<Text>{message||"No demo payment records."}</Text>}</Screen>;
}
const styles=StyleSheet.create({warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center"},stack:{gap:6},title:{fontWeight:"900",color:colors.forest},caption:{fontSize:12,color:"#64748B"}});
