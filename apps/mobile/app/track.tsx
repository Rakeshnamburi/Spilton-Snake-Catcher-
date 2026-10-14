import {useState} from "react";
import {useRouter} from "expo-router";
import {Button,HelperText,TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {InfoCard} from "@/components/cards";
import type {IncidentListItem, Paginated} from "@/features/incidents/types";
import {STATUS_TRANSLATION_KEYS} from "@/features/incidents/status";
import {api, normalizePage} from "@/services/api";
import {localizedError} from "@/services/errors";
import {useI18n} from "@/services/i18n";

export default function Track(){
  const router=useRouter();
  const {t}=useI18n();
  const [reference,setReference]=useState("");
  const [result,setResult]=useState<IncidentListItem|null>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);

  async function lookup(){
    const normalizedReference=reference.trim().toUpperCase();
    if(!/^SPR-[A-Z0-9-]{8,32}$/.test(normalizedReference)){
      setError("Enter a valid incident reference.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try{
      let pageNumber=1;
      let pageCount=1;
      do {
        const page=normalizePage(await api<Paginated<IncidentListItem>|IncidentListItem[]>(`/api/v1/incidents/mine?page=${pageNumber}&page_size=100`));
        const match=page.items.find(i=>i.reference_code.toUpperCase()===normalizedReference);
        if(match){
          setResult(match);
          return;
        }
        pageCount=page.pages;
        pageNumber+=1;
      } while(pageNumber<=pageCount);
      setError("No matching incident belongs to this signed-in account.");
    }catch(e){
      setResult(null);
      setError(localizedError(e,t));
    }finally{
      setLoading(false);
    }
  }

  return <Screen title={t("navTrack")} subtitle="A reference alone is not sufficient. Your signed-in account must own the incident.">
    <TextInput label={t("reference")} autoCapitalize="characters" value={reference} onChangeText={setReference}/>
    <Button mode="contained" loading={loading} disabled={loading} onPress={()=>void lookup()}>Check status</Button>
    <HelperText type="error" visible={!!error}>{error}</HelperText>
    {result&&<InfoCard title={`${result.reference_code} · ${t(STATUS_TRANSLATION_KEYS[result.status])}`}>
      {result.city}, {result.district}, {result.state}{"\n"}{t("demoOnly")}
    </InfoCard>}
    {result&&<Button compact mode="outlined" onPress={()=>router.push(`/incidents/${result.id}`)}>{t("viewReport")}</Button>}
    <Button onPress={()=>router.push("/login")}>{t("signIn")}</Button>
  </Screen>
}
