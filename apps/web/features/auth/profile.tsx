"use client";

import {useEffect, useState} from "react";
import {useRouter} from "next/navigation";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {useI18n} from "@/lib/i18n";

type User = {name: string; email: string; phone: string; role: string};
type DataRequest = {id: string; request_type: "EXPORT" | "DELETION"; status: string; created_at: string};

export function ProfileManager() {
  const router = useRouter();
  const {t} = useI18n();
  const [user, setUser] = useState<User | null>(null);
  const [requests, setRequests] = useState<DataRequest[]>([]);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const [profile, privacyRequests] = await Promise.all([
        api<User>("/api/v1/auth/me"),
        api<DataRequest[]>("/api/v1/auth/account-requests"),
      ]);
      setUser(profile);
      setRequests(privacyRequests);
      setError("");
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 401 ? t("profile.signInRequired") : reason instanceof Error ? reason.message : t("error.network"));
    }
  }

  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user || busy) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<User>("/api/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify({...user, current_password: password}),
      });
      setUser(updated);
      setPassword("");
      setNotice(t("profile.saved"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("error.network"));
    } finally {
      setBusy(false);
    }
  }

  async function requestData(requestType: "EXPORT" | "DELETION") {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api<DataRequest>("/api/v1/auth/account-requests", {
        method: "POST",
        body: JSON.stringify({request_type: requestType}),
      });
      setNotice(t(requestType === "EXPORT" ? "profile.exportRequested" : "profile.deletionRequested"));
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("error.network"));
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    try {
      await api<void>("/api/v1/auth/logout", {method: "POST"});
      router.replace("/login");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("error.network"));
      setBusy(false);
    }
  }

  if (!user) return <div className="card" role={error ? "alert" : "status"}>{error || t("profile.loading")}</div>;
  return <div className="grid gap-7 lg:grid-cols-[1fr_.8fr]">
    <form className="card space-y-5" onSubmit={save}>
      <div><p className="eyebrow">{t("profile.account")}</p><h2 className="mt-2 text-2xl font-black">{t("profile.details")}</h2><p className="mt-2 text-sm text-slate-600">{t("profile.passwordNotice")}</p></div>
      <label className="block"><span className="label">{t("auth.name")}</span><input className="field" value={user.name} onChange={(event) => setUser({...user, name: event.target.value})} required minLength={2}/></label>
      <label className="block"><span className="label">{t("auth.email")}</span><input className="field" type="email" value={user.email} onChange={(event) => setUser({...user, email: event.target.value})} required/></label>
      <label className="block"><span className="label">{t("auth.phone")}</span><input className="field" type="tel" value={user.phone} onChange={(event) => setUser({...user, phone: event.target.value})} required pattern="\+?[0-9]{10,15}"/></label>
      <label className="block"><span className="label">{t("profile.currentPassword")}</span><input className="field" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required/></label>
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm font-semibold text-danger" role="alert">{error}</p>}
      {notice && <p className="rounded-xl bg-green-50 p-3 text-sm font-semibold text-forest" role="status">{notice}</p>}
      <Button disabled={busy}>{busy ? t("common.working") : t("profile.save")}</Button>
      <Button type="button" className="ml-3 bg-slate-700" disabled={busy} onClick={() => void signOut()}>{t("profile.signOut")}</Button>
    </form>
    <section className="card"><p className="eyebrow">{t("profile.privacy")}</p><h2 className="mt-2 text-2xl font-black">{t("profile.dataRequests")}</h2><p className="mt-3 text-sm leading-6 text-slate-600">{t("profile.dataRequestNotice")}</p><div className="mt-6 flex flex-wrap gap-3"><Button type="button" disabled={busy} onClick={() => void requestData("EXPORT")}>{t("profile.requestExport")}</Button><Button type="button" className="bg-slate-700" disabled={busy} onClick={() => void requestData("DELETION")}>{t("profile.requestDeletion")}</Button></div><ul className="mt-7 space-y-3">{requests.map((item) => <li key={item.id} className="rounded-xl bg-mist p-4 text-sm"><strong>{item.request_type}</strong> · {item.status}<span className="mt-1 block text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span></li>)}</ul></section>
  </div>;
}
