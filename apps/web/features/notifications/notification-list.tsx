"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {BellRing} from "lucide-react";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";

type Notice = {
  id: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  deep_link: string | null;
  event_type: string;
};

export function NotificationList() {
  const [items, setItems] = useState<Notice[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setItems(await api<Notice[]>("/api/v1/notifications/mine"));
      setError("");
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? "Sign in to see your notifications."
          : reason instanceof Error
            ? reason.message
            : "Unable to load notifications.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function markRead(id: string) {
    try {
      await api(`/api/v1/notifications/${encodeURIComponent(id)}/read`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await load();
    } catch {
      /* leave the item as it is */
    }
  }

  if (loading) return <div className="card" role="status">Loading notifications…</div>;
  if (error) return <div className="card border-red-200" role="alert"><p className="text-sm font-semibold text-danger">{error}</p><Link href="/login" className="mt-3 inline-block font-bold text-forest">Sign in</Link></div>;
  if (!items.length) return <div className="card text-center"><BellRing className="mx-auto text-forest"/><h2 className="mt-4 text-xl font-black">No notifications yet</h2><p className="mt-2 text-sm text-slate-600">New booking requests, approvals and chat messages appear here.</p><Link href="/rescuers" className="mt-5 inline-block rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white">Find a catcher</Link></div>;

  return <div className="space-y-3">{items.map((item) => <article key={item.id} className={`card ${item.read_at ? "" : "border-l-4 border-l-danger"}`}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-black uppercase tracking-wide text-slate-500">{item.event_type.replaceAll("_", " ")}</p>
        <h3 className="mt-1 font-black text-forest">{item.title}</h3>
        <p className="mt-1 text-sm leading-6 text-slate-600">{item.body}</p>
      </div>
      <time className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</time>
    </div>
    <div className="mt-3 flex gap-3">
      {item.deep_link && <Link href={item.deep_link} className="text-sm font-bold text-forest">Open →</Link>}
      {!item.read_at && <Button type="button" className="bg-slate-200 text-forest" onClick={() => void markRead(item.id)}>Mark as read</Button>}
    </div>
  </article>)}</div>;
}
