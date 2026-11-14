import {useLocalSearchParams, useRouter} from "expo-router";
import {useState} from "react";
import {Button, HelperText, Text, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {api, saveToken} from "@/services/api";

type LoginResponse = {access_token?: string | null};

export default function VerifyEmailScreen() {
  const router = useRouter();
  const {email: initialEmail} = useLocalSearchParams<{email?: string}>();
  const [email, setEmail] = useState(initialEmail ?? "");
  const [code, setCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function verify() {
    if (!email.trim() || !code.trim()) return setError("Enter your email and the code.");
    setBusy(true);
    setError("");
    try {
      const result = await api<LoginResponse>("/api/v1/auth/email/verify", {
        method: "POST",
        body: JSON.stringify({email: email.trim(), code: code.trim()}),
      });
      if (result.access_token) await saveToken(result.access_token);
      router.replace("/report");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not confirm that code.");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{dev_code?: string}>("/api/v1/auth/email/resend", {
        method: "POST",
        body: JSON.stringify({email: email.trim()}),
      });
      setNotice(result.dev_code ? `Development code: ${result.dev_code}` : "A fresh code is on its way.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not resend the code.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title="Confirm your email" subtitle="New accounts must confirm their address before signing in.">
      <TextInput mode="outlined" label="Email" keyboardType="email-address" autoCapitalize="none" value={email} onChangeText={setEmail}/>
      <TextInput mode="outlined" label="Confirmation code" keyboardType="number-pad" value={code} onChangeText={value => setCode(value.replace(/\D/g, ""))} maxLength={10}/>
      {notice ? <Text>{notice}</Text> : null}
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      <Button mode="contained" loading={busy} disabled={busy} onPress={() => void verify()}>Confirm and continue</Button>
      <Button disabled={busy} onPress={() => void resend()}>Resend code</Button>
      <Button disabled={busy} onPress={() => router.replace("/login")}>Back to sign in</Button>
    </Screen>
  );
}
