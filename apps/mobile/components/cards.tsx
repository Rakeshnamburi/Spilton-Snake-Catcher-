import {ReactNode} from "react";
import {StyleSheet,View} from "react-native";
import {Text} from "react-native-paper";
import {colors} from "@/services/theme";
export function InfoCard({title,children,danger=false}:{title:string;children:ReactNode;danger?:boolean}){return <View style={[styles.card,danger&&styles.danger]}><Text variant="titleMedium" style={[styles.title,danger&&{color:"white"}]}>{title}</Text><Text style={[styles.text,danger&&{color:"#fee2e2"}]}>{children}</Text></View>}
const styles=StyleSheet.create({card:{backgroundColor:"white",padding:18,borderRadius:16,borderWidth:1,borderColor:"#e2e8f0"},danger:{backgroundColor:colors.danger,borderColor:colors.danger},title:{fontWeight:"800",color:colors.forest},text:{marginTop:8,lineHeight:22,color:"#475569"}});

