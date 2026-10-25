"use client";

import {FormEvent, useCallback, useEffect, useRef, useState} from "react";
import {Send} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";
import {formatDate} from "@/lib/marketplace";

type Message = {
  id: string;
  sender_id: string;
  sender_role: string;
  body: string;
  created_at: string;
};

/**
 * In-app chat between the customer and the assigned demo rescuer. Phone numbers
 * and emails stay hidden; this is the only contact channel inside a booking.
 */
export function BookingChat({bookingId}: {bookingId: string}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      setMessages(
        await api<Message[]>(`/api/v1/bookings/${encodeURIComponent(bookingId)}/messages`),
      );
      setError("");
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? "Sign in to use in-app chat."
          : reason instanceof Error
            ? reason.message
            : "Chat is unavailable.",
      );
    }
  }, [bookingId]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 8000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    endRef.current?.scrollIntoView({block: "nearest"});
  }, [messages.length]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    setBusy(true);
    try {
      await api(`/api/v1/bookings/${encodeURIComponent(bookingId)}/messages`, {
        method: "POST",
        body: JSON.stringify({body: draft.trim()}),
      });
      setDraft("");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Message could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="card">
    <h2 className="text-xl font-black">Message in the app</h2>
    <p className="mt-2 text-sm text-slate-600">Phone numbers and emails stay hidden. Tell your rescuer exactly where the snake is, or how to find your gate.</p>
    <div className="mt-5 max-h-80 space-y-3 overflow-y-auto rounded-xl bg-mist p-4">
      {messages.length === 0
        ? <p className="text-sm text-slate-500">No messages yet. Say hello to your demo rescuer.</p>
        : messages.map((message) => <div key={message.id} className={`max-w-[85%] rounded-2xl p-3 text-sm ${message.sender_role === "CUSTOMER" ? "ml-auto bg-forest text-white" : "bg-white"}`}>
            <p className="text-[11px] font-bold uppercase opacity-70">{message.sender_role === "CUSTOMER" ? "You" : "Demo rescuer"} · {formatDate(message.created_at)}</p>
            <p className="mt-1 leading-6">{message.body}</p>
          </div>)}
      <div ref={endRef}/>
    </div>
    <form className="mt-4 flex items-end gap-2" onSubmit={send}>
      <label className="flex-1"><span className="sr-only">Message</span><input className="field" maxLength={1000} placeholder="Type a message" value={draft} onChange={(event) => setDraft(event.target.value)}/></label>
      <Button disabled={busy} type="submit"><Send size={16}/> {busy ? "Sending…" : "Send"}</Button>
    </form>
    {error && <p className="mt-3 text-sm font-semibold text-danger" role="alert">{error}</p>}
  </section>;
}
