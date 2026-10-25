"use client";

import {useCallback, useEffect, useState} from "react";
import {PhoneCall, ShieldCheck} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";

type Contact = {
  proxy_number: string;
  label: string;
  masked: boolean;
  real_number_hidden: boolean;
  counterpart_role: string;
  connectable: boolean;
  available_from: string;
  message: string;
};

/**
 * Masked calling line, like a delivery app's proxy number. The counterpart's
 * real phone number is never sent to the browser — only this platform proxy.
 */
export function BookingContact({bookingId}: {bookingId: string}) {
  const [contact, setContact] = useState<Contact | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setContact(await api<Contact>(`/api/v1/bookings/${encodeURIComponent(bookingId)}/contact`));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Masked line unavailable.");
    }
  }, [bookingId]);

  useEffect(() => { void load(); }, [load]);

  if (error) return null;
  if (!contact) return null;

  const who = contact.counterpart_role === "CUSTOMER" ? "the customer" : "your rescuer";

  return <section className="card">
    <div className="flex items-center gap-3"><PhoneCall className="text-forest"/><h2 className="text-xl font-black">Masked calling line</h2></div>
    <p className="mt-2 text-sm text-slate-600">Call {who} without sharing either real phone number. Calls route through a platform proxy number, exactly like a delivery app.</p>
    <div className="mt-5 rounded-2xl bg-mist p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{contact.label}</p>
      <p className="mt-2 text-3xl font-black tracking-wide text-forest">{contact.proxy_number}</p>
      <p className="mt-3 flex items-center gap-2 text-xs font-bold text-emerald"><ShieldCheck size={15}/> Real number hidden from both sides</p>
    </div>
    <p className={`mt-4 text-sm leading-6 ${contact.connectable ? "font-bold text-forest" : "text-slate-600"}`}>{contact.message}</p>
    <div className="mt-5 flex flex-wrap gap-3">
      <Button disabled={!contact.connectable} onClick={() => window.alert(`Demo only — in production this would connect the call through ${contact.proxy_number}. No real call is placed.`)}>
        <PhoneCall size={16}/> {contact.connectable ? "Call via masked line" : "Masked line not active yet"}
      </Button>
      <span className="self-center text-xs text-slate-500">Demo mode: no real call is placed.</span>
    </div>
  </section>;
}
