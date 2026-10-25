"use client";

import Link from "next/link";
import {useState} from "react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";

type Stage = "email" | "code" | "done";

export function ForgotPasswordForm() {
  const [stage, setStage] = useState<Stage>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function requestCode(event: React.FormEvent) {
    event.preventDefault();
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
          ? `Development mode: your reset code is ${result.dev_code}`
          : "If an account exists for that address, a reset code is on its way. It expires in a few minutes.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send the reset code.");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (password.length < 10) {
      setError("Use at least 10 characters.");
      return;
    }
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/auth/password/reset", {
        method: "POST",
        body: JSON.stringify({email: email.trim(), code: code.trim(), new_password: password}),
      });
      setStage("done");
      setNotice("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reset the password.");
    } finally {
      setBusy(false);
    }
  }

  if (stage === "done") {
    return <div className="card mx-auto max-w-lg space-y-5 text-center">
      <h2 className="text-2xl font-black text-forest">Password updated</h2>
      <p className="text-sm leading-6 text-slate-600">
        Your password has been changed and every other signed-in session was signed out.
      </p>
      <Link href="/login" className="inline-flex justify-center rounded-xl bg-forest px-6 py-3 font-bold text-white">Go to sign in</Link>
    </div>;
  }

  if (stage === "code") {
    return <form onSubmit={resetPassword} className="card mx-auto max-w-lg space-y-5" noValidate>
      {notice && <p className="rounded-lg bg-mist p-3 text-sm text-slate-700" role="status">{notice}</p>}
      <label className="block"><span className="label">Reset code</span>
        <input className="field tracking-[0.3em]" inputMode="numeric" autoComplete="one-time-code" maxLength={10} required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}/>
      </label>
      <label className="block"><span className="label">New password</span>
        <input className="field" type="password" autoComplete="new-password" required value={password} onChange={(event) => setPassword(event.target.value)}/>
        <small className="text-slate-500">At least 10 characters.</small>
      </label>
      <label className="block"><span className="label">Confirm new password</span>
        <input className="field" type="password" autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)}/>
      </label>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{error}</p>}
      <Button className="w-full" disabled={busy}>{busy ? "Updating…" : "Set new password"}</Button>
      <button type="button" className="w-full text-sm font-semibold text-slate-500" onClick={() => {setStage("email"); setError(""); setNotice("");}}>
        Use a different email
      </button>
    </form>;
  }

  return <form onSubmit={requestCode} className="card mx-auto max-w-lg space-y-5" noValidate>
    <label className="block"><span className="label">Email address</span>
      <input className="field" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)}/>
    </label>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{error}</p>}
    <Button className="w-full" disabled={busy}>{busy ? "Sending…" : "Email me a reset code"}</Button>
    <p className="text-center text-sm text-slate-600">
      <Link className="font-bold text-forest" href="/login">Back to sign in</Link>
    </p>
  </form>;
}
