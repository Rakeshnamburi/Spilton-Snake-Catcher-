import {Href, useRouter} from "expo-router";
import {useEffect, useState} from "react";
import {Button, Text, TextInput} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {api, clearToken} from "@/services/api";
import {registerDeviceForDemoNotifications} from "@/services/notifications";
import {useI18n} from "@/services/i18n";

type User = {name: string; email: string; phone: string; role: string};

export default function Profile() {
  const router = useRouter();
  const {t} = useI18n();
  const [user, setUser] = useState<User | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    api<User>("/api/v1/auth/me").then(setUser).catch((reason) => setError(reason.message));
  }, []);
  if (error && !user) {
    return <Screen title={t("navProfile")}><InfoCard title={t("profileSignInRequired")}>{error}</InfoCard><Button mode="contained" onPress={() => router.push("/login")}>{t("signIn")}</Button></Screen>;
  }
  async function saveProfile() {
    if (!user || !password || busy) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<User>("/api/v1/auth/me", {method:"PATCH", body:JSON.stringify({...user, current_password:password})});
      setUser(updated);
      setPassword("");
      setNotice(t("profileSaved"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("genericError"));
    } finally { setBusy(false); }
  }
  async function privacyRequest(request_type:"EXPORT"|"DELETION") {
    setBusy(true);
    try {
      await api("/api/v1/auth/account-requests", {method:"POST", body:JSON.stringify({request_type})});
      setNotice(t("profileRequestRecorded"));
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : t("genericError"));
    } finally { setBusy(false); }
  }
  return <Screen title={t("navProfile")} subtitle={t("profileSubtitle")}>
    {user ? <>
      <InfoCard title={user.role}>{user.email}{"\n"}{user.phone}</InfoCard>
      <TextInput mode="outlined" label={t("profileName")} value={user.name} onChangeText={name => setUser({...user,name})}/>
      <TextInput mode="outlined" label={t("profileEmail")} keyboardType="email-address" autoCapitalize="none" value={user.email} onChangeText={email => setUser({...user,email})}/>
      <TextInput mode="outlined" label={t("profilePhone")} keyboardType="phone-pad" value={user.phone} onChangeText={phone => setUser({...user,phone})}/>
      <TextInput mode="outlined" label={t("profileCurrentPassword")} secureTextEntry value={password} onChangeText={setPassword}/>
      <Button mode="contained" loading={busy} disabled={busy || !password} onPress={() => void saveProfile()}>{t("profileSave")}</Button>
      <Button mode="outlined" disabled={busy} onPress={() => void privacyRequest("EXPORT")}>{t("profileExport")}</Button>
      <Button mode="outlined" disabled={busy} onPress={() => void privacyRequest("DELETION")}>{t("profileDelete")}</Button>
    </> : <Text>{t("profileLoading")}</Text>}
    <Button mode="contained-tonal" icon="receipt" onPress={() => router.push("/payments" as Href)}>My demo payments</Button>
    {user?.role === "RESCUER" ? <Button mode="contained-tonal" icon="cash-multiple" onPress={() => router.push("/rescuer-earnings" as Href)}>Illustrative earnings</Button> : null}
    <Button mode="contained-tonal" icon="bell-outline" onPress={async () => {
      try {
        const device = await registerDeviceForDemoNotifications();
        setNotice(`Demo push device registered ${device.token_hint}. No real dispatch messages are sent.`);
      } catch (reason) {
        setNotice(reason instanceof Error ? reason.message : "Notification registration failed.");
      }
    }}>Enable demo push updates</Button>
    {notice ? <InfoCard title="Notification status">{notice}</InfoCard> : null}
    {error && user ? <InfoCard title="Unable to save">{error}</InfoCard> : null}
    <Button mode="outlined" disabled={busy} onPress={async () => {
      setBusy(true);
      try { await api<void>("/api/v1/auth/logout", {method:"POST"}); }
      catch { setNotice("Server session could not be revoked; this device session was removed."); }
      finally { await clearToken(); router.replace("/home"); }
    }}>{t("profileSignOut")}</Button>
  </Screen>;
}
