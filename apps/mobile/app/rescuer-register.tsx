import {useEffect, useState} from "react";
import {ScrollView, StyleSheet, View} from "react-native";
import {Button, Checkbox, Text, TextInput} from "react-native-paper";
import {LocationDirectory} from "@/components/location-directory";
import {Screen} from "@/components/screen";
import {EMPTY_LOCATION} from "@/features/marketplace/context";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";

export default function RescuerRegisterScreen() {
  const [location, setLocation] = useState(EMPTY_LOCATION);
  const [displayName, setDisplayName] = useState("");
  const [organization, setOrganization] = useState("");
  const [experience, setExperience] = useState("");
  const [languages, setLanguages] = useState("");
  const [training, setTraining] = useState("");
  const [reference, setReference] = useState("");
  const [authority, setAuthority] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [coverage, setCoverage] = useState("");
  const [mandals, setMandals] = useState<{lgd_code: string; name: string}[]>([]);
  const [travelMandals, setTravelMandals] = useState<string[]>([]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!location.district_code) { setMandals([]); return; }
    api<{items: {lgd_code: string; name: string}[]}>(
      `/api/v1/locations/subdistricts?district_code=${encodeURIComponent(location.district_code)}&limit=100`,
    ).then(result => setMandals(result.items)).catch(() => setMandals([]));
  }, [location.district_code]);

  function toggleTravelMandal(code: string) {
    setTravelMandals(current => current.includes(code) ? current.filter(item => item !== code) : [...current, code]);
  }

  async function submit() {
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api<{id:string;verification_status:string}>("/api/v1/rescuers/onboarding", {method:"POST",body:JSON.stringify({public_display_name:displayName,state_code:location.state_code,district_code:location.district_code,subdistrict_code:location.subdistrict_code || undefined,village_code:location.village_code || undefined,organization_name:organization,years_experience:Number(experience),languages:languages.split(",").map(item => item.trim()).filter(Boolean),training_details:training,authorization_reference:reference,issuing_authority:authority,authorization_issue_date:issueDate,authorization_expiry:expiryDate,service_area_description:coverage,service_radius_km:25,coverage_subdistrict_codes:travelMandals,operating_hours:{},acknowledgement:acknowledged})});
      setMessage(`Application ${result.id} is ${result.verification_status}. No role was granted automatically.`);
    } catch (reason) { setError(reason instanceof ApiError && reason.status === 401 ? "Sign in with a citizen account first." : reason instanceof Error ? reason.message : "Application failed."); }
    finally { setBusy(false); }
  }
  return <Screen title="Rescuer onboarding" subtitle="Submit a demo application for administrator review. This does not grant legal or platform verification.">
    <View style={styles.warning}><Text style={styles.warningText}>PUBLIC SIGNUP NEVER GRANTS VERIFIED OR RESCUER STATUS.</Text></View>
    <TextInput mode="outlined" label="Public display name" value={displayName} onChangeText={setDisplayName}/>
    <TextInput mode="outlined" label="Organization affiliation" value={organization} onChangeText={setOrganization}/>
    <TextInput mode="outlined" label="Relevant experience (years)" keyboardType="numeric" value={experience} onChangeText={setExperience}/>
    <TextInput mode="outlined" label="Languages, comma separated" value={languages} onChangeText={setLanguages}/>
    <TextInput mode="outlined" label="Training details" multiline value={training} onChangeText={setTraining}/>
    <LocationDirectory value={location} onChange={value => setLocation({...location, ...value})}/>
    {mandals.length > 0 ? <View style={styles.mandalBlock}>
      <Text variant="titleSmall">Other mandals you will travel to</Text>
      <Text style={styles.note}>Optional. Tick mandals besides your own; customers there will see a "Serves your mandal" badge.</Text>
      <ScrollView style={styles.mandalList} nestedScrollEnabled>
        {mandals.map(item => <View style={styles.checkRow} key={item.lgd_code}><Checkbox status={travelMandals.includes(item.lgd_code) ? "checked" : "unchecked"} onPress={() => toggleTravelMandal(item.lgd_code)}/><Text style={styles.checkText} onPress={() => toggleTravelMandal(item.lgd_code)}>{item.name}</Text></View>)}
      </ScrollView>
      {travelMandals.length > 0 ? <Text style={styles.success}>{travelMandals.length} extra mandal(s) selected</Text> : null}
    </View> : null}
    <TextInput mode="outlined" label="Service coverage description" multiline value={coverage} onChangeText={setCoverage}/>
    <TextInput mode="outlined" label="Authorization reference" value={reference} onChangeText={setReference}/>
    <TextInput mode="outlined" label="Issuing authority" value={authority} onChangeText={setAuthority}/>
    <View style={styles.row}><TextInput style={styles.flex} mode="outlined" label="Issue date YYYY-MM-DD" value={issueDate} onChangeText={setIssueDate}/><TextInput style={styles.flex} mode="outlined" label="Expiry date YYYY-MM-DD" value={expiryDate} onChangeText={setExpiryDate}/></View>
    <View style={styles.checkRow}><Checkbox status={acknowledged ? "checked" : "unchecked"} onPress={() => setAcknowledged(value => !value)}/><Text style={styles.checkText} onPress={() => setAcknowledged(value => !value)}>I understand application status does not replace legal wildlife authorization and requires privileged administrator review.</Text></View>
    <Text style={styles.note}>Private evidence upload is available in the web onboarding flow. Approval is blocked until at least one evidence file is stored.</Text>
    {error ? <Text style={styles.error}>{error}</Text> : null}{message ? <Text style={styles.success}>{message}</Text> : null}
    <Button mode="contained" loading={busy} disabled={busy} onPress={() => void submit()}>Submit demo application</Button>
  </Screen>;
}

const styles=StyleSheet.create({mandalBlock:{gap:6},mandalList:{maxHeight:220,borderWidth:1,borderColor:"#E2E8F0",borderRadius:12},warning:{backgroundColor:"#FEF2F2",borderRadius:12,padding:14},warningText:{color:colors.danger,fontWeight:"900"},row:{flexDirection:"row",gap:8},flex:{flex:1},checkRow:{flexDirection:"row",alignItems:"center"},checkText:{flex:1,fontSize:13,lineHeight:19},note:{fontSize:12,lineHeight:18,color:"#64748B"},error:{color:colors.danger,fontWeight:"700"},success:{color:colors.forest,fontWeight:"700"}});
