import {useLocalSearchParams, useRouter} from "expo-router";
import {useEffect, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, Chip, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {useMarketplace} from "@/features/marketplace/context";
import type {PublicRescuer} from "@/features/marketplace/types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

export default function RescuerProfileScreen() {
  const {id} = useLocalSearchParams<{id:string}>();
  const router = useRouter();
  const {selectedRescuer, setSelectedRescuer} = useMarketplace();
  const [rescuer, setRescuer] = useState<PublicRescuer | null>(selectedRescuer?.id === id ? selectedRescuer : null);
  const [error, setError] = useState("");
  useEffect(() => { if (!id) return; api<PublicRescuer>(`/api/v1/rescuers/${encodeURIComponent(id)}`).then(value => {setRescuer(value); setSelectedRescuer(value);}).catch(reason => setError(reason instanceof Error ? reason.message : "Profile unavailable.")); }, [id, setSelectedRescuer]);
  return <Screen title="Demo rescuer profile" subtitle="Public-safe fields only. Identity documents, home address and exact coordinates remain private.">
    <View style={styles.warning}><Text style={styles.warningText}>FICTIONAL PROFILE — simulated verification is not a claim of real authorization.</Text></View>
    {error ? <Text style={styles.error}>{error}</Text> : null}
    {!rescuer && !error ? <Text>Loading protected profile…</Text> : null}
    {rescuer ? <Card><Card.Content style={styles.stack}><Chip compact>SIMULATED {rescuer.verification_status}</Chip><Text variant="headlineSmall" style={styles.title}>{rescuer.display_name}</Text><Text variant="titleMedium">{rescuer.organization}</Text><Text>{rescuer.years_experience} years supplied experience</Text><Text>{rescuer.languages.join(", ")}</Text><Text style={styles.body}>{rescuer.service_area}</Text><Text>Availability: {rescuer.availability} (demo)</Text><Text>{rescuer.review_count ? `${rescuer.average_rating} simulated rating` : "No demo reviews yet"}</Text><Text>{rescuer.completed_service_count} simulated completed services; not real performance history.</Text><Text style={styles.money}>Charges and payments disabled.</Text>{rescuer.availability === "AVAILABLE" ? <Button mode="contained" onPress={() => router.push({pathname:"/book/[rescuerId]",params:{rescuerId:rescuer.id}})}>Request simulated assistance</Button> : <Button disabled>Not accepting demo requests</Button>}</Card.Content></Card> : null}
  </Screen>;
}

const styles=StyleSheet.create({warning:{backgroundColor:"#FFFBEB",borderRadius:12,padding:14},warningText:{color:"#78350F",fontWeight:"900"},error:{color:colors.danger,fontWeight:"700"},stack:{gap:10},title:{fontWeight:"900",color:colors.forest},body:{lineHeight:21,color:"#475569"},money:{fontWeight:"800",color:colors.forest}});
