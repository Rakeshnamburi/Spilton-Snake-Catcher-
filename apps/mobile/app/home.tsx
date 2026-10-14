import {useRouter} from "expo-router";
import {Button} from "react-native-paper";
import {Screen} from "@/components/screen";
import {InfoCard} from "@/components/cards";
import {LanguageSelector} from "@/components/language-selector";
import {useI18n} from "@/services/i18n";

export default function Home(){
  const router=useRouter();
  const {t}=useI18n();
  return <Screen title={t("homeTitle")} subtitle={t("homeSubtitle")}>
    <LanguageSelector />
    <Button mode="contained" icon="alert-circle-outline" onPress={()=>router.push("/report")}>{t("reportAction")}</Button>
    <Button mode="outlined" icon="format-list-bulleted" onPress={()=>router.push("/my-reports")}>{t("reportsAction")}</Button>
    <Button mode="contained-tonal" icon="account-search" onPress={()=>router.push("/nearby-rescuers")}>Nearby demo rescuers</Button>
    <Button mode="outlined" icon="calendar-check" onPress={()=>router.push("/bookings")}>My demo bookings</Button>
    <Button mode="outlined" icon="shield-account" onPress={()=>router.push("/rescuer-dashboard")}>Rescuer workspace</Button>
    <Button mode="outlined" icon="map-marker-check" onPress={()=>router.push("/track")}>{t("trackAction")}</Button>
    <Button mode="outlined" icon="shield-check" onPress={()=>router.push("/safety")}>{t("safetyAction")}</Button>
    <Button mode="contained" buttonColor="#DC2626" icon="phone" onPress={()=>router.push("/emergency")}>{t("emergencyAction")}</Button>
    <InfoCard title="Future coverage vision">Andhra Pradesh, Telangana, Karnataka, Tamil Nadu, and Kerala. This is not current operational coverage.</InfoCard>
    <Button compact onPress={()=>router.push("/profile")}>{t("navProfile")}</Button>
  </Screen>
}
