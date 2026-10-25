import {useEffect, useRef, useState} from "react";
import {useLocalSearchParams, useRouter} from "expo-router";
import {Button, Divider, HelperText, Text, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import {api, saveToken} from "@/services/api";
import {fetchProviders, requestOtp, startSocial, verifyOtp, type Providers} from "@/services/auth";

type LoginResponse = {access_token?: string | null};

export default function Login() {
  const router = useRouter();
  const {returnTo} = useLocalSearchParams<{returnTo?: string}>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submitLock = useRef(false);

  const [providers, setProviders] = useState<Providers | null>(null);
  const [otpOpen, setOtpOpen] = useState(false);
  const [otpStage, setOtpStage] = useState<"email" | "code">("email");
  const [otpEmail, setOtpEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpNotice, setOtpNotice] = useState("");
  const [otpError, setOtpError] = useState("");
  const [otpBusy, setOtpBusy] = useState(false);

  useEffect(() => {
    fetchProviders().then(setProviders).catch(() => setProviders(null));
  }, []);

  function nextRoute() {
    return returnTo === "report" ? "/report-reporter" : "/profile";
  }

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
      router.replace(nextRoute());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to sign in");
    } finally {
      submitLock.current = false;
      setSubmitting(false);
    }
  }

  async function sendOtp() {
    if (!otpEmail.trim()) {
      setOtpError("Enter your email address.");
      return;
    }
    setOtpBusy(true);
    setOtpError("");
    setOtpNotice("");
    try {
      const result = await requestOtp(otpEmail);
      setOtpStage("code");
      setOtpNotice(
        result.dev_code
          ? `Development code: ${result.dev_code}`
          : `We emailed a one-time code to ${otpEmail.trim()}.`,
      );
    } catch (requestError) {
      setOtpError(requestError instanceof Error ? requestError.message : "Could not send the code.");
    } finally {
      setOtpBusy(false);
    }
  }

  async function confirmOtp() {
    if (!otpCode.trim()) {
      setOtpError("Enter the code from your email.");
      return;
    }
    setOtpBusy(true);
    setOtpError("");
    try {
      await verifyOtp(otpEmail, otpCode);
      router.replace(nextRoute());
    } catch (requestError) {
      setOtpError(requestError instanceof Error ? requestError.message : "Could not verify the code.");
    } finally {
      setOtpBusy(false);
    }
  }

  async function social(provider: "google" | "microsoft") {
    setError("");
    try {
      await startSocial(provider, returnTo);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not open the sign-in page.");
    }
  }

  return (
    <Screen title="Sign in" subtitle="Your token is stored in the device’s secure credential store.">
      {providers?.google && (
        <Button mode="outlined" icon="google" disabled={submitting} onPress={() => void social("google")}>
          Continue with Google
        </Button>
      )}
      {providers?.microsoft && (
        <Button mode="outlined" icon="microsoft" disabled={submitting} onPress={() => void social("microsoft")}>
          Continue with Microsoft
        </Button>
      )}
      {(providers?.google || providers?.microsoft) && <Divider />}

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
      <Button disabled={submitting} onPress={() => router.push("/forgot-password")}>Forgot password?</Button>

      <Divider />
      <Button disabled={submitting} onPress={() => setOtpOpen(value => !value)}>
        {otpOpen ? "Hide one-time code sign-in" : "Sign in with an email one-time code (OTP)"}
      </Button>
      {otpOpen && otpStage === "email" && (
        <>
          <TextInput
            label="Email for one-time code"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            value={otpEmail}
            onChangeText={setOtpEmail}
          />
          <HelperText type="error" visible={Boolean(otpError)}>{otpError}</HelperText>
          <Button mode="outlined" loading={otpBusy} disabled={otpBusy} onPress={() => void sendOtp()}>
            Email me a code
          </Button>
        </>
      )}
      {otpOpen && otpStage === "code" && (
        <>
          {otpNotice ? <Text>{otpNotice}</Text> : null}
          <TextInput
            label="One-time code"
            keyboardType="number-pad"
            value={otpCode}
            onChangeText={value => setOtpCode(value.replace(/\D/g, ""))}
          />
          <HelperText type="error" visible={Boolean(otpError)}>{otpError}</HelperText>
          <Button mode="contained" loading={otpBusy} disabled={otpBusy} onPress={() => void confirmOtp()}>
            Verify and sign in
          </Button>
          <Button disabled={otpBusy} onPress={() => {setOtpStage("email"); setOtpError(""); setOtpNotice("");}}>
            Use a different email
          </Button>
        </>
      )}

      <Button
        disabled={submitting}
        onPress={() => router.replace({pathname: "/register", params: returnTo ? {returnTo} : {}})}
      >
        Create citizen account
      </Button>
    </Screen>
  );
}
