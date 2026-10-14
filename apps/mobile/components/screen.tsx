import {ReactNode} from "react";
import {ScrollView,StyleSheet,View} from "react-native";
import {Text} from "react-native-paper";
import {colors} from "@/services/theme";
import {useI18n} from "@/services/i18n";
export function Screen({title,subtitle,children}:{title:string;subtitle?:string;children:ReactNode}){const {t}=useI18n();return <ScrollView keyboardShouldPersistTaps="handled" style={styles.page} contentContainerStyle={styles.content}><View accessibilityRole="alert" style={styles.warning}><Text style={styles.warningText}>{t("demoBanner")}</Text></View><Text variant="headlineMedium" style={styles.title}>{title}</Text>{subtitle&&<Text style={styles.subtitle}>{subtitle}</Text>}<View style={styles.body}>{children}</View></ScrollView>}
const styles=StyleSheet.create({page:{flex:1,backgroundColor:colors.mist},content:{padding:20,paddingBottom:48},warning:{backgroundColor:colors.danger,borderRadius:10,padding:10,marginBottom:24},warningText:{color:"white",fontSize:11,fontWeight:"800",textAlign:"center"},title:{fontWeight:"900",color:colors.forest},subtitle:{color:"#475569",lineHeight:22,marginTop:7},body:{gap:14,marginTop:24}});
