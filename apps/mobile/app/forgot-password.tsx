import {useState} from "react";
import {useRouter} from "expo-router";
import {Button, HelperText, Text, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {api} from "@/services/api";

type Stage = "email" | "code" | "done";

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function requestCode() {
    if (!email.trim()) return setError("Enter your email address.");
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api<{sent: boolean; dev_code?: string}>("/api/v1/auth/password/forgot", {
        method: "POST",
        body: JSON.stringify({email: email.trim()}),
      });
      setStage("code");
      setNotice(
        result.dev_code
          ? `Development code: ${result.dev_code}`
          : "If an account exists for that address, a reset code is on its way.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send the reset code.");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword() {
    if (password.length < 10) return setError("Use at least 10 characters.");
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/password/reset", {
        method: "POST",
        body: JSON.stringify({email: email.trim(), code: code.trim(), new_password: password}),
      });
      setStage("done");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reset the password.");
    } finally {
      setBusy(false);
    }
  }

  if (stage === "done") {
    return (
      <Screen title="Password updated" subtitle="Every other signed-in session was signed out.">
        <Button mode="contained" onPress={() => router.replace("/login")}>Go to sign in</Button>
      </Screen>
    );
  }

  if (stage === "code") {
    return (
      <Screen title="Set a new password" subtitle="Enter the code we emailed you.">
        {notice ? <Text>{notice}</Text> : null}
        <TextInput mode="outlined" label="Reset code" keyboardType="number-pad" value={code} onChangeText={value => setCode(value.replace(/\D/g, ""))} maxLength={10}/>
        <TextInput mode="outlined" label="New password (10+ characters)" secureTextEntry autoCapitalize="none" value={password} onChangeText={setPassword}/>
        <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
        <Button mode="contained" loading={busy} disabled={busy} onPress={() => void resetPassword()}>Set new password</Button>
        <Button disabled={busy} onPress={() => {setStage("email"); setError(""); setNotice("");}}>Use a different email</Button>
      </Screen>
    );
  }

  return (
    <Screen title="Reset your password" subtitle="We email a one-time code. Changing the password signs out other sessions.">
      <TextInput mode="outlined" label="Email" keyboardType="email-address" autoCapitalize="none" autoCorrect={false} value={email} onChangeText={setEmail}/>
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      <Button mode="contained" loading={busy} disabled={busy} onPress={() => void requestCode()}>Email me a reset code</Button>
      <Button disabled={busy} onPress={() => router.replace("/login")}>Back to sign in</Button>
    </Screen>
  );
}
