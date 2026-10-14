import {useRef, useState} from "react";
import {useLocalSearchParams, useRouter} from "expo-router";
import {Button, HelperText, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {api, saveToken} from "@/services/api";

type LoginResponse = {access_token?: string | null};

export default function Login() {
  const router = useRouter();
  const {returnTo} = useLocalSearchParams<{returnTo?: string}>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submitLock = useRef(false);

  async function submit() {
    if (submitLock.current) return;
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    submitLock.current = true;
    setSubmitting(true);
    setError("");
    try {
      const result = await api<LoginResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({email: email.trim(), password}),
      });
      if (!result.access_token) throw new Error("The server did not return a mobile access token.");
      await saveToken(result.access_token);
      router.replace(returnTo === "report" ? "/report-reporter" : "/profile");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to sign in");
    } finally {
      submitLock.current = false;
      setSubmitting(false);
    }
  }

  return (
    <Screen title="Sign in" subtitle="Your token is stored in the device’s secure credential store.">
      <TextInput
        label="Email"
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        label="Password"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        value={password}
        onChangeText={setPassword}
      />
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      <Button mode="contained" loading={submitting} disabled={submitting} onPress={() => void submit()}>Sign in</Button>
      <Button
        disabled={submitting}
        onPress={() => router.replace({pathname: "/register", params: returnTo ? {returnTo} : {}})}
      >
        Create citizen account
      </Button>
    </Screen>
  );
}
