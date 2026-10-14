import {useRef, useState} from "react";
import {useLocalSearchParams, useRouter} from "expo-router";
import {Button, HelperText, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {api, saveToken} from "@/services/api";

type LoginResponse = {access_token?: string | null};

export default function Register() {
  const router = useRouter();
  const {returnTo} = useLocalSearchParams<{returnTo?: string}>();
  const [form, setForm] = useState({name: "", email: "", phone: "", password: ""});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submitLock = useRef(false);

  async function submit() {
    if (submitLock.current) return;
    const payload = {
      name: form.name.trim(),
      email: form.email.trim(),
      phone: form.phone.replace(/[\s()-]/g, ""),
      password: form.password,
    };
    if (payload.name.length < 2) {
      setError("Enter your name.");
      return;
    }
    if (!/^\+?[0-9]{10,15}$/.test(payload.phone)) {
      setError("Enter a 10–15 digit contact number.");
      return;
    }
    if (payload.password.length < 10) {
      setError("Password must contain at least 10 characters.");
      return;
    }
    submitLock.current = true;
    setSubmitting(true);
    setError("");
    try {
      const result = await api<LoginResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!result.access_token) throw new Error("The server did not return a mobile access token.");
      await saveToken(result.access_token);
      router.replace(returnTo === "report" ? "/report-reporter" : "/report");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to register");
    } finally {
      submitLock.current = false;
      setSubmitting(false);
    }
  }

  const fields = Object.keys(form) as Array<keyof typeof form>;
  return (
    <Screen title="Citizen registration" subtitle="Privileged roles cannot be selected during public registration.">
      {fields.map(key => (
        <TextInput
          key={key}
          label={key[0].toUpperCase() + key.slice(1)}
          secureTextEntry={key === "password"}
          keyboardType={key === "phone" ? "phone-pad" : key === "email" ? "email-address" : "default"}
          autoCapitalize={key === "email" || key === "password" ? "none" : "sentences"}
          autoCorrect={key !== "email" && key !== "password"}
          value={form[key]}
          onChangeText={value => setForm(current => ({...current, [key]: value}))}
        />
      ))}
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      <Button mode="contained" loading={submitting} disabled={submitting} onPress={() => void submit()}>Create account</Button>
    </Screen>
  );
}
