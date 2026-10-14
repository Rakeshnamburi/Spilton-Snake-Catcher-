import * as ExpoLocation from "expo-location";
import {useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Text, TextInput} from "react-native-paper";
import {LocationDirectory} from "@/components/location-directory";
import {Screen} from "@/components/screen";
import {useMarketplace} from "@/features/marketplace/context";
import {colors} from "@/services/theme";

export default function MarketplaceLocationScreen() {
  const {location, setLocation} = useMarketplace();
  const [draft, setDraft] = useState(location);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function locate() {
    setBusy(true);
    setMessage("Requesting foreground location permission…");
    try {
      const permission = await ExpoLocation.requestForegroundPermissionsAsync();
      if (!permission.granted) {
        setMessage("Permission denied. Manual address and LGD selection remain fully usable.");
        return;
      }
      const current = await ExpoLocation.getCurrentPositionAsync({accuracy: ExpoLocation.Accuracy.High});
      setDraft(value => ({...value, latitude:Number(current.coords.latitude.toFixed(6)), longitude:Number(current.coords.longitude.toFixed(6)), accuracy:current.coords.accuracy ?? undefined}));
      setMessage(`Location captured with ±${Math.round(current.coords.accuracy ?? 0)} m accuracy. Confirm the directory yourself.`);
    } catch {
      setMessage("Location could not be captured. Use manual entry instead.");
    } finally {
      setBusy(false);
    }
  }

  return <Screen title="Select marketplace location" subtitle="Use foreground GPS after consent or enter a manual location. GPS never proves a village address.">
    <View style={styles.notice}><Text style={styles.noticeText}>DEMO LOCATION ONLY — no live responder is dispatched.</Text></View>
    <LocationDirectory value={draft} onChange={value => setDraft({...draft, ...value})}/>
    <TextInput mode="outlined" label="Manual address description" multiline value={draft.manualAddress} onChangeText={manualAddress => setDraft(value => ({...value, manualAddress}))}/>
    <TextInput mode="outlined" label="Landmark (optional)" value={draft.landmark} onChangeText={landmark => setDraft(value => ({...value, landmark}))}/>
    <View style={styles.row}><TextInput style={styles.flex} mode="outlined" label="Latitude" keyboardType="numbers-and-punctuation" value={draft.latitude?.toString() ?? ""} onChangeText={value => setDraft(current => ({...current, latitude:value ? Number(value) : undefined}))}/><TextInput style={styles.flex} mode="outlined" label="Longitude" keyboardType="numbers-and-punctuation" value={draft.longitude?.toString() ?? ""} onChangeText={value => setDraft(current => ({...current, longitude:value ? Number(value) : undefined}))}/></View>
    <Button mode="contained" icon="crosshairs-gps" loading={busy} disabled={busy} onPress={() => void locate()}>Use current location</Button>
    {message ? <Text style={styles.message}>{message}</Text> : null}
    <Button mode="contained-tonal" onPress={() => {setLocation(draft); setMessage("Location saved for the current marketplace flow.");}}>Save confirmed location</Button>
  </Screen>;
}

const styles=StyleSheet.create({notice:{backgroundColor:"#FEF2F2",borderRadius:12,padding:14},noticeText:{color:colors.danger,fontWeight:"800"},row:{flexDirection:"row",gap:10},flex:{flex:1},message:{fontSize:13,lineHeight:20,color:"#475569"}});
