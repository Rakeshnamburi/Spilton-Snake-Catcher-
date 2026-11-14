"use client";

import Link from "next/link";
import {useRouter, useSearchParams} from "next/navigation";
import {Suspense, useState} from "react";
import {MailCheck} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";

function VerifyInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function verify(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/email/verify", {
        method: "POST",
        body: JSON.stringify({email: email.trim(), code: code.trim()}),
      });
      router.push("/track");
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
      setNotice(
        result.dev_code
          ? `Development mode: your code is ${result.dev_code}`
          : "If that address needs confirming, a fresh code is on its way.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not resend the code.");
    } finally {
      setBusy(false);
    }
  }

  return <form onSubmit={verify} className="card mx-auto max-w-lg space-y-5" noValidate>
    <div className="flex items-center gap-3"><MailCheck className="text-forest"/><h2 className="text-2xl font-black text-forest">Confirm your email</h2></div>
    <p className="text-sm leading-6 text-slate-600">
      We sent a confirmation code to your address. Enter it to finish signing up — you cannot sign in until the address is confirmed.
    </p>
    <label className="block"><span className="label">Email address</span>
      <input className="field" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)}/>
    </label>
    <label className="block"><span className="label">Confirmation code</span>
      <input className="field tracking-[0.3em]" inputMode="numeric" autoComplete="one-time-code" maxLength={10} required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}/>
    </label>
    {notice && <p className="rounded-lg bg-mist p-3 text-sm text-slate-700" role="status">{notice}</p>}
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{error}</p>}
    <Button className="w-full" disabled={busy}>{busy ? "Confirming…" : "Confirm and continue"}</Button>
    <div className="flex items-center justify-between text-sm">
      <button type="button" className="font-semibold text-forest" onClick={() => void resend()} disabled={busy}>Resend code</button>
      <Link className="font-semibold text-slate-500" href="/login">Back to sign in</Link>
    </div>
  </form>;
}

export function VerifyEmailForm() {
  return <Suspense fallback={<div className="card mx-auto max-w-lg">Loading…</div>}><VerifyInner/></Suspense>;
}
