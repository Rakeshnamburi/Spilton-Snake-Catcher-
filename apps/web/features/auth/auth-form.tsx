"use client";

import Link from "next/link";
import {useRouter} from "next/navigation";
import {useEffect, useMemo, useState} from "react";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {Button} from "@/components/ui/button";
import {api, API_URL} from "@/lib/api";
import {useI18n} from "@/lib/i18n";

type Mode = "login" | "register";
type Values = {name?: string; email: string; phone?: string; password: string};
type Providers = {password: boolean; email_otp: boolean; google: boolean; microsoft: boolean};

function makeSchema(mode: Mode): z.ZodType<Values> {
  return z.object({
    name: mode === "register" ? z.string().trim().min(2, "Enter your full name.").max(120) : z.string().optional(),
    email: z.string().trim().email("Enter a valid email address."),
    phone: mode === "register"
      ? z.string().regex(/^\+?[0-9]{10,15}$/, "Enter 10–15 digits, optionally beginning with +.")
      : z.string().optional(),
    password: mode === "register"
      ? z.string().min(10, "Use at least 10 characters.").max(128)
      : z.string().min(1, "Enter your password.").max(128),
  });
}

export function AuthForm({mode}: {mode: Mode}) {
  const router = useRouter();
  const {t} = useI18n();
  const schema = useMemo(() => makeSchema(mode), [mode]);
  const {register, handleSubmit, formState: {errors, isSubmitting}, setError} = useForm<Values>({resolver: zodResolver(schema)});

  const [providers, setProviders] = useState<Providers>({password: true, email_otp: true, google: false, microsoft: false});
  const [otpOpen, setOtpOpen] = useState(false);
  const [otpEmail, setOtpEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpStage, setOtpStage] = useState<"email" | "code">("email");
  const [otpBusy, setOtpBusy] = useState(false);
  const [otpError, setOtpError] = useState("");
  const [otpNotice, setOtpNotice] = useState("");

  useEffect(() => {
    api<Providers>("/api/v1/auth/providers").then(setProviders).catch(() => undefined);
  }, []);

  async function submit(values: Values) {
    try {
      await api(`/api/v1/auth/${mode}`, {method: "POST", body: JSON.stringify(values)});
      router.push(mode === "login" ? "/track" : "/report");
    } catch (reason) {
      setError("root", {message: reason instanceof Error ? reason.message : "Unable to continue."});
    }
  }

  function startSocial(provider: "google" | "microsoft") {
    const returnTo = mode === "login" ? "/track" : "/report";
    window.location.href = `${API_URL}/api/v1/auth/oauth/${provider}/start?mode=web&return_to=${encodeURIComponent(returnTo)}`;
  }

  async function requestOtp(event: React.FormEvent) {
    event.preventDefault();
    setOtpBusy(true);
    setOtpError("");
    setOtpNotice("");
    try {
      const result = await api<{transport: string; dev_code?: string}>("/api/v1/auth/otp/request", {
        method: "POST",
        body: JSON.stringify({email: otpEmail}),
      });
      setOtpStage("code");
      setOtpNotice(
        result.dev_code
          ? `Development mode: your code is ${result.dev_code}`
          : `We emailed a one-time code to ${otpEmail}. It expires in a few minutes.`,
      );
    } catch (reason) {
      setOtpError(reason instanceof Error ? reason.message : "Could not send the code.");
    } finally {
      setOtpBusy(false);
    }
  }

  async function verifyOtp(event: React.FormEvent) {
    event.preventDefault();
    setOtpBusy(true);
    setOtpError("");
    try {
      await api("/api/v1/auth/otp/verify", {
        method: "POST",
        body: JSON.stringify({email: otpEmail, code: otpCode}),
      });
      router.push(mode === "login" ? "/track" : "/report");
    } catch (reason) {
      setOtpError(reason instanceof Error ? reason.message : "Could not verify the code.");
    } finally {
      setOtpBusy(false);
    }
  }

  const socialAvailable = providers.google || providers.microsoft;

  return <div className="mx-auto max-w-lg space-y-5">
    {socialAvailable && <div className="card space-y-3">
      {providers.google && <button type="button" onClick={() => startSocial("google")}
        className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 hover:bg-mist">
        <span className="text-lg font-black text-[#4285F4]">G</span> Continue with Google
      </button>}
      {providers.microsoft && <button type="button" onClick={() => startSocial("microsoft")}
        className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 hover:bg-mist">
        <span className="grid grid-cols-2 gap-[2px]">{["#F25022","#7FBA00","#00A4EF","#FFB900"].map(c => <span key={c} className="h-2 w-2" style={{background: c}}/>)}</span> Continue with Microsoft
      </button>}
      <div className="flex items-center gap-3 text-xs font-semibold uppercase text-slate-400">
        <span className="h-px flex-1 bg-slate-200"/>or<span className="h-px flex-1 bg-slate-200"/>
      </div>
    </div>}

    <form onSubmit={handleSubmit(submit)} className="card space-y-5" noValidate>
      {mode === "register" && <>
        <label className="block"><span className="label">{t("auth.name")}</span><input className="field" autoComplete="name" {...register("name")}/>{errors.name && <small className="text-danger">{errors.name.message}</small>}</label>
        <label className="block"><span className="label">{t("auth.phone")}</span><input className="field" type="tel" inputMode="tel" autoComplete="tel" {...register("phone")}/>{errors.phone && <small className="text-danger">{errors.phone.message}</small>}</label>
      </>}
      <label className="block"><span className="label">{t("auth.email")}</span><input className="field" type="email" autoComplete="email" {...register("email")}/><small className="text-danger">{errors.email?.message}</small></label>
      <label className="block"><span className="label">{t("auth.password")}</span><input className="field" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} {...register("password")}/><small className="text-danger">{errors.password?.message}</small></label>
      {errors.root && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{errors.root.message}</p>}
      <Button className="w-full" disabled={isSubmitting}>{isSubmitting ? t("auth.wait") : mode === "login" ? t("auth.signIn") : t("auth.register")}</Button>
      <p className="text-center text-sm text-slate-600">{mode === "login" ? `${t("auth.new")} ` : `${t("auth.existing")} `}<Link className="font-bold text-forest" href={mode === "login" ? "/register" : "/login"}>{mode === "login" ? t("auth.create") : t("nav.signIn")}</Link></p>
    </form>

    <div className="card space-y-4">
      <button type="button" onClick={() => setOtpOpen(v => !v)} className="flex w-full items-center justify-between text-left font-bold text-forest">
        <span>Sign in with an email one-time code (OTP)</span>
        <span className="text-xl">{otpOpen ? "−" : "+"}</span>
      </button>

      {otpOpen && (otpStage === "email"
        ? <form onSubmit={requestOtp} className="space-y-4" noValidate>
            <label className="block"><span className="label">Email address</span>
              <input className="field" type="email" autoComplete="email" required value={otpEmail} onChange={e => setOtpEmail(e.target.value)}/></label>
            {otpError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{otpError}</p>}
            <Button className="w-full" disabled={otpBusy}>{otpBusy ? "Sending…" : "Email me a code"}</Button>
          </form>
        : <form onSubmit={verifyOtp} className="space-y-4" noValidate>
            {otpNotice && <p className="rounded-lg bg-mist p-3 text-sm text-slate-700">{otpNotice}</p>}
            <label className="block"><span className="label">Enter the {providers.email_otp ? "6-digit" : ""} code</span>
              <input className="field tracking-[0.4em]" inputMode="numeric" autoComplete="one-time-code" maxLength={10} required value={otpCode} onChange={e => setOtpCode(e.target.value.replace(/\D/g, ""))}/></label>
            {otpError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{otpError}</p>}
            <Button className="w-full" disabled={otpBusy}>{otpBusy ? "Verifying…" : "Verify and sign in"}</Button>
            <button type="button" className="w-full text-sm font-semibold text-slate-500" onClick={() => {setOtpStage("email"); setOtpError(""); setOtpNotice("");}}>Use a different email</button>
          </form>)}
    </div>
  </div>;
}
