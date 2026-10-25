import * as Linking from "expo-linking";
import {API_URL, api, saveToken} from "@/services/api";

export type Providers = {password: boolean; email_otp: boolean; google: boolean; microsoft: boolean};
export type AuthSession = {access_token?: string | null};
export type OtpRequestResult = {
  sent: boolean;
  transport: string;
  dev_code?: string;
  expires_in_seconds: number;
};

export function fetchProviders() {
  return api<Providers>("/api/v1/auth/providers");
}

export async function requestOtp(email: string) {
  return api<OtpRequestResult>("/api/v1/auth/otp/request", {
    method: "POST",
    body: JSON.stringify({email: email.trim()}),
  });
}

export async function verifyOtp(email: string, code: string) {
  const result = await api<AuthSession>("/api/v1/auth/otp/verify", {
    method: "POST",
    body: JSON.stringify({email: email.trim(), code: code.trim()}),
  });
  if (result.access_token) await saveToken(result.access_token);
  return result;
}

export function socialStartUrl(provider: "google" | "microsoft", returnTo?: string) {
  const params = new URLSearchParams({mode: "mobile"});
  if (returnTo) params.set("return_to", returnTo);
  return `${API_URL}/api/v1/auth/oauth/${provider}/start?${params.toString()}`;
}

/**
 * Opens the provider consent screen in the system browser. The API redirects
 * back to spilton://auth-callback?code=..., which expo-router routes to the
 * /auth-callback screen where the code is exchanged for a bearer session.
 */
export async function startSocial(provider: "google" | "microsoft", returnTo?: string) {
  await Linking.openURL(socialStartUrl(provider, returnTo));
}

export async function completeSocial(code: string) {
  const result = await api<AuthSession>("/api/v1/auth/oauth/exchange", {
    method: "POST",
    body: JSON.stringify({code}),
  });
  if (result.access_token) await saveToken(result.access_token);
  return result;
}
