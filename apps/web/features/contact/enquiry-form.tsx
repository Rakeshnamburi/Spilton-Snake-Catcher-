"use client";

import {useState} from "react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";

export function EnquiryForm() {
  const [form, setForm] = useState({name: "", email: "", phone: "", subject: "", message: ""});
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({...current, [field]: value}));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/enquiries", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || null,
          subject: form.subject.trim(),
          message: form.message.trim(),
        }),
      });
      setSent(true);
      setForm({name: "", email: "", phone: "", subject: "", message: ""});
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send your message.");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return <div className="card mx-auto max-w-2xl text-center">
      <h2 className="text-2xl font-black text-forest">Message sent</h2>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Thank you — we reply to the address you gave. For anything urgent about a snake, do not wait for an email.
      </p>
      <button type="button" className="mt-5 rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white" onClick={() => setSent(false)}>
        Send another message
      </button>
    </div>;
  }

  return <form onSubmit={submit} className="card mx-auto max-w-2xl space-y-5" noValidate>
    <label className="block"><span className="label">Name</span>
      <input className="field" required value={form.name} onChange={(event) => update("name", event.target.value)}/>
    </label>
    <label className="block"><span className="label">Email</span>
      <input className="field" type="email" required value={form.email} onChange={(event) => update("email", event.target.value)}/>
    </label>
    <label className="block"><span className="label">Phone (optional)</span>
      <input className="field" value={form.phone} onChange={(event) => update("phone", event.target.value)}/>
    </label>
    <label className="block"><span className="label">Subject</span>
      <input className="field" required value={form.subject} onChange={(event) => update("subject", event.target.value)}/>
    </label>
    <label className="block"><span className="label">Message</span>
      <textarea className="field min-h-36" required value={form.message} onChange={(event) => update("message", event.target.value)}/>
    </label>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{error}</p>}
    <Button className="w-full" disabled={busy}>{busy ? "Sending…" : "Send message"}</Button>
    <p className="text-xs text-slate-500">Do not use this form for emergencies. Call 112 for immediate medical help.</p>
  </form>;
}
