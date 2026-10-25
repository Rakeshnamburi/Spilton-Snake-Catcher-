import {useEffect, useState} from "react";
import {useLocalSearchParams, useRouter} from "expo-router";
import {ActivityIndicator, Button, Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {completeSocial} from "@/services/auth";

/**
 * Handles the spilton://auth-callback deep link returned by the social sign-in
 * flow, exchanging the one-time code for a bearer session.
 */
export default function AuthCallback() {
  const router = useRouter();
  const params = useLocalSearchParams<{status?: string; code?: string; reason?: string}>();
  const [message, setMessage] = useState("Finishing sign-in…");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      if (params.status === "error") {
        if (!active) return;
        setFailed(true);
        setMessage(
          params.reason === "provider_not_configured"
            ? "That sign-in provider is not configured on the server yet."
            : "We could not complete sign-in. Please try again.",
        );
        return;
      }
      if (!params.code) {
        if (!active) return;
        setFailed(true);
        setMessage("The sign-in response was missing its code.");
        return;
      }
      try {
        await completeSocial(params.code);
        if (active) router.replace("/profile");
      } catch (error) {
        if (!active) return;
        setFailed(true);
        setMessage(error instanceof Error ? error.message : "Could not complete sign-in.");
      }
    })();
    return () => {
      active = false;
    };
  }, [params.code, params.reason, params.status, router]);

  return (
    <Screen title="Signing you in" subtitle={message}>
      {!failed && <ActivityIndicator animating />}
      {failed && <Button mode="contained" onPress={() => router.replace("/login")}>Back to sign in</Button>}
      {!failed && <Text>Please wait while we confirm your session.</Text>}
    </Screen>
  );
}
