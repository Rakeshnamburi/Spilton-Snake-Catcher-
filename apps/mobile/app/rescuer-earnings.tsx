import {useFocusEffect} from "expo-router";
import {useCallback, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {api} from "@/services/api";
import {colors} from "@/services/theme";
import type {DemoPayment} from "@spilton/shared-types";

type Earnings={gross_demo_amount:string;commission_demo_amount:string;rescuer_demo_share:string;reversed_demo_amount:string;withdrawable:false;disclaimer:string};
export default function RescuerEarningsScreen(){
 const[data,setData]=useState<Earnings|null>(null);const[message,setMessage]=useState("");
 const[transactions,setTransactions]=useState<DemoPayment[]>([]);const[busy,setBusy]=useState("");
 const load=useCallback(async()=>{try{const[earnings,rows]=await Promise.all([api<Earnings>("/api/v1/rescuer/earnings"),api<DemoPayment[]>("/api/v1/rescuer/transactions")]);setData(earnings);setTransactions(rows);setMessage("");}catch(reason){setMessage(reason instanceof Error?reason.message:"Earnings unavailable.");}},[]);
 useFocusEffect(useCallback(()=>{void load();},[load]));
 async function confirmCash(id:string){setBusy(id);try{await api("/api/v1/payments/"+id+"/cash-confirm",{method:"POST",body:JSON.stringify({confirm_received:true})});setMessage("Simulated cash receipt confirmed. No real funds moved.");await load();}catch(reason){setMessage(reason instanceof Error?reason.message:"Cash confirmation failed.");}finally{setBusy("");}}
 return <Screen title="Illustrative earnings" subtitle="Demo accounting only; withdrawals are disabled."><View style={styles.warning}><Text style={styles.warningText}>NO REAL EARNINGS · NO WITHDRAWAL · NO PAYOUT</Text></View>{data?<><Card><Card.Content style={styles.stack}><Text variant="headlineMedium" style={styles.title}>₹{data.rescuer_demo_share}</Text><Text>Illustrative rescuer share</Text><Text>Gross: ₹{data.gross_demo_amount}</Text><Text>Platform commission: ₹{data.commission_demo_amount}</Text><Text>Reversed commission: ₹{data.reversed_demo_amount}</Text></Card.Content></Card><Text style={styles.caption}>{data.disclaimer}</Text><Text variant="titleLarge" style={styles.title}>Assigned demo transactions</Text>{transactions.map((item)=><Card key={item.id}><Card.Content style={styles.stack}><Text style={styles.bold}>{item.payment_reference}</Text><Text>₹{item.amount} · {item.status.replaceAll("_"," ")}</Text><Text style={styles.caption}>No real funds moved.</Text>{item.method==="DEMO_CASH"&&item.status==="CASH_AWAITING_CONFIRMATION"?<Button mode="contained" loading={busy===item.id} onPress={()=>void confirmCash(item.id)}>Confirm simulated cash</Button>:null}</Card.Content></Card>)}{!transactions.length?<Text>No assigned demo transactions.</Text>:null}</>:<Text>{message||"Loading…"}</Text>}{message?<Text style={styles.message}>{message}</Text>:null}</Screen>;
}
const styles=StyleSheet.create({warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},warningText:{color:"white",fontWeight:"900",textAlign:"center"},stack:{gap:8},title:{fontWeight:"900",color:colors.forest},caption:{fontSize:12,color:"#64748B"},bold:{fontWeight:"800"},message:{color:"#92400E",fontWeight:"700"}});
