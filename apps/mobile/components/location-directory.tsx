import {useEffect, useState} from "react";
import {FlatList, Modal, Pressable, StyleSheet, View} from "react-native";
import {Button, Text} from "react-native-paper";
import type {DirectoryLocation, LocationItem, MarketplacePage} from "@/features/marketplace/types";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

function DirectoryPicker({label, value, options, disabled, onSelect}: {label: string; value: string; options: LocationItem[]; disabled?: boolean; onSelect: (item: LocationItem) => void}) {
  const [open, setOpen] = useState(false);
  const selected = options.find(item => item.lgd_code === value);
  return <View>
    <Text variant="labelLarge">{label}</Text>
    <Button mode="outlined" disabled={disabled} style={styles.button} contentStyle={styles.buttonContent} onPress={() => setOpen(true)}>{selected?.name ?? `Select ${label.toLowerCase()}`}</Button>
    <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
      <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
        <Pressable style={styles.sheet} onPress={event => event.stopPropagation()}>
          <Text variant="titleLarge" style={styles.heading}>{label}</Text>
          <FlatList data={options} keyExtractor={item => item.lgd_code} ListEmptyComponent={<Text style={styles.empty}>No imported official LGD entries are available.</Text>} renderItem={({item}) => <Pressable accessibilityRole="button" style={styles.option} onPress={() => {onSelect(item); setOpen(false);}}><Text variant="bodyLarge">{item.name}</Text><Text variant="bodySmall">LGD {item.lgd_code}</Text></Pressable>}/>
          <Button onPress={() => setOpen(false)}>Close</Button>
        </Pressable>
      </Pressable>
    </Modal>
  </View>;
}

export function LocationDirectory({value, onChange}: {value: DirectoryLocation; onChange: (value: DirectoryLocation) => void}) {
  const [states, setStates] = useState<LocationItem[]>([]);
  const [districts, setDistricts] = useState<LocationItem[]>([]);
  const [subdistricts, setSubdistricts] = useState<LocationItem[]>([]);
  const [villages, setVillages] = useState<LocationItem[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<MarketplacePage<LocationItem>>("/api/v1/locations/states?limit=100").then(result => setStates(result.items)).catch(reason => setError(reason instanceof Error ? reason.message : "Location directory unavailable.")); }, []);
  useEffect(() => {
    if (!value.state_code) return setDistricts([]);
    api<MarketplacePage<LocationItem>>(`/api/v1/locations/districts?state_code=${encodeURIComponent(value.state_code)}&limit=100`).then(result => setDistricts(result.items)).catch(() => setDistricts([]));
  }, [value.state_code]);
  useEffect(() => {
    if (!value.district_code) return setSubdistricts([]);
    api<MarketplacePage<LocationItem>>(`/api/v1/locations/subdistricts?district_code=${encodeURIComponent(value.district_code)}&limit=100`).then(result => setSubdistricts(result.items)).catch(() => setSubdistricts([]));
  }, [value.district_code]);
  useEffect(() => {
    if (!value.subdistrict_code) return setVillages([]);
    api<MarketplacePage<LocationItem>>(`/api/v1/locations/villages?subdistrict_code=${encodeURIComponent(value.subdistrict_code)}&limit=100`).then(result => setVillages(result.items)).catch(() => setVillages([]));
  }, [value.subdistrict_code]);
  return <View style={styles.group}>
    <DirectoryPicker label="State / Union Territory" value={value.state_code} options={states} onSelect={item => onChange({...value, state_code:item.lgd_code, district_code:"", subdistrict_code:"", village_code:""})}/>
    <DirectoryPicker label="District" value={value.district_code} options={districts} disabled={!value.state_code} onSelect={item => onChange({...value, district_code:item.lgd_code, subdistrict_code:"", village_code:""})}/>
    <DirectoryPicker label="Subdistrict / mandal / taluk / tehsil" value={value.subdistrict_code} options={subdistricts} disabled={!value.district_code} onSelect={item => onChange({...value, subdistrict_code:item.lgd_code, village_code:""})}/>
    <DirectoryPicker label="Village" value={value.village_code} options={villages} disabled={!value.subdistrict_code} onSelect={item => onChange({...value, village_code:item.lgd_code})}/>
    {error ? <Text style={styles.error}>{error}</Text> : null}
    {!states.length && !error ? <Text style={styles.note}>No official LGD data is bundled. An administrator must import a current Government of India export.</Text> : null}
    <Text style={styles.note}>GPS is not treated as a verified village address. Confirm or correct the directory selection.</Text>
  </View>;
}

const styles=StyleSheet.create({group:{gap:12},button:{marginTop:6,borderColor:"#CBD5E1"},buttonContent:{minHeight:48,justifyContent:"flex-start"},backdrop:{flex:1,backgroundColor:"rgba(15,23,42,.55)",justifyContent:"flex-end"},sheet:{maxHeight:"75%",backgroundColor:"white",borderTopLeftRadius:24,borderTopRightRadius:24,padding:20},heading:{fontWeight:"900",color:colors.forest,marginBottom:12},option:{paddingVertical:14,borderBottomWidth:1,borderBottomColor:"#E2E8F0"},empty:{padding:24,textAlign:"center",color:"#64748B"},note:{fontSize:12,lineHeight:18,color:"#64748B"},error:{fontSize:12,color:colors.danger,fontWeight:"700"}});
