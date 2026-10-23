import {useRouter} from "expo-router";
import {useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Chip, Text, TextInput} from "react-native-paper";
import {LocationDirectory} from "@/components/location-directory";
import {Screen} from "@/components/screen";
import {useMarketplace} from "@/features/marketplace/context";
import type {MarketplacePage, PublicRescuer} from "@/features/marketplace/types";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";
import {useI18n} from "@/services/i18n";

export default function NearbyRescuersScreen() {
  const router = useRouter();
  const {t} = useI18n();
  const {location, setLocation, setSelectedRescuer} = useMarketplace();
  const [radius, setRadius] = useState("25");
  const [language, setLanguage] = useState("");
  const [result, setResult] = useState<MarketplacePage<PublicRescuer> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search() {
    if (!location.state_code && (location.latitude === undefined || location.longitude === undefined)) {
      setError("Select an imported LGD state or capture coordinates first.");
      return;
    }
    setLoading(true);
    setError("");
    const query = new URLSearchParams({radius_km:radius || "25"});
    if (location.state_code) query.set("state_code", location.state_code);
    if (location.district_code) query.set("district_code", location.district_code);
    if (location.latitude !== undefined && location.longitude !== undefined) {
      query.set("latitude", String(location.latitude));
      query.set("longitude", String(location.longitude));
    }
    if (language.trim()) query.set("language", language.trim());
    try {
      setResult(await api<MarketplacePage<PublicRescuer>>(`/api/v1/rescuers/nearby?${query}`));
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return <Screen title="Nearby demo rescuers" subtitle="Only fictional profiles passing verification, organization, expiry, availability, coverage and distance checks appear.">
    <View style={styles.warning}><Text style={styles.warningText}>NOT LIVE AVAILABILITY — no search result is an emergency-service promise.</Text></View>
    <LocationDirectory value={location} onChange={value => setLocation({...location, ...value})}/>
    <View style={styles.row}><TextInput style={styles.flex} mode="outlined" label="Radius km" keyboardType="numeric" value={radius} onChangeText={setRadius}/><TextInput style={styles.flex} mode="outlined" label="Language" value={language} onChangeText={setLanguage}/></View>
    <Button mode="outlined" icon="map-marker" onPress={() => router.push("/marketplace-location")}>GPS or manual location</Button>
    <Button mode="contained" loading={loading} disabled={loading} onPress={() => void search()}>{t("marketplaceSearch")}</Button>
    {error ? <Text style={styles.error}>{error}</Text> : null}
    {result && result.items.length === 0 ? <Card><Card.Content><Text variant="titleMedium" style={styles.cardTitle}>{t("marketplaceNoRescuer")}</Text><Text style={styles.body}>Use the verified public emergency directory. This prototype cannot dispatch assistance.</Text><Button onPress={() => router.push("/emergency")}>{t("marketplaceEmergency")}</Button></Card.Content></Card> : null}
    {result?.items.map(rescuer => <Card key={rescuer.id}><Card.Content style={styles.stack}><Chip compact>FICTIONAL DEMO PROFILE</Chip><Text variant="titleLarge" style={styles.cardTitle}>{rescuer.display_name}</Text><Text>{rescuer.organization}</Text><Text style={styles.body}>{rescuer.years_experience} years supplied experience · {rescuer.languages.join(", ")}</Text><Text style={styles.body}>{rescuer.distance_km === null ? "Directory coverage match" : `Approximately ${rescuer.distance_km} km`} · {rescuer.availability} (demo)</Text><Text style={styles.body}>{rescuer.service_area}</Text><View style={styles.row}><Button style={styles.flex} mode="outlined" onPress={() => {setSelectedRescuer(rescuer); router.push({pathname:"/rescuers/[id]",params:{id:rescuer.id}});}}>{t("marketplaceProfile")}</Button><Button style={styles.flex} mode="contained" onPress={() => {setSelectedRescuer(rescuer); router.push({pathname:"/book/[rescuerId]",params:{rescuerId:rescuer.id}});}}>{t("marketplaceRequest")}</Button></View></Card.Content></Card>)}
  </Screen>;
}

const styles=StyleSheet.create({warning:{backgroundColor:"#FEF2F2",borderRadius:12,padding:14},warningText:{color:colors.danger,fontWeight:"900",fontSize:12},row:{flexDirection:"row",gap:10},flex:{flex:1},error:{color:colors.danger,fontWeight:"700"},stack:{gap:10},cardTitle:{fontWeight:"900",color:colors.forest},body:{color:"#475569",lineHeight:20}});
