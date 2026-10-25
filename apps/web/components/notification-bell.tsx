"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {Bell} from "lucide-react";
import {api} from "@/lib/api";

type Notice = {
  id: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  deep_link: string | null;
};

/**
 * Bell in the header. Polls the signed-in user's notifications so new requests,
 * accepts, approvals and chat messages show up without a manual refresh.
 */
export function NotificationBell() {
  const [items, setItems] = useState<Notice[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const result = await api<Notice[]>("/api/v1/notifications/mine");
        if (alive) setItems(result);
      } catch {
        if (alive) setItems([]);
      }
    }
    void load();
    const timer = window.setInterval(load, 20000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const unread = items.filter((item) => !item.read_at).length;
  const recent = items.slice(0, 6);

  return <div className="relative">
    <button
      type="button"
      aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
      className="relative grid h-10 w-10 place-items-center rounded-xl border border-slate-300 text-slate-600 hover:text-forest"
      onClick={() => setOpen((value) => !value)}
    >
      <Bell size={18}/>
      {unread > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-danger px-1 text-[10px] font-black text-white">{unread > 9 ? "9+" : unread}</span>}
    </button>
    {open && <div className="absolute right-0 z-50 mt-2 w-80 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
      <p className="px-3 py-2 text-xs font-black uppercase tracking-wide text-slate-500">Notifications</p>
      {recent.length === 0
        ? <p className="px-3 pb-3 text-sm text-slate-500">Nothing yet. New requests and approvals will appear here.</p>
        : recent.map((item) => <Link key={item.id} href={item.deep_link || "/notifications"} className="block rounded-xl px-3 py-2 hover:bg-mist" onClick={() => setOpen(false)}>
            <span className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${item.read_at ? "bg-slate-300" : "bg-danger"}`}/><strong className="text-sm text-forest">{item.title}</strong></span>
            <span className="mt-1 block text-xs leading-5 text-slate-600">{item.body}</span>
          </Link>)}
      <Link href="/notifications" className="mt-1 block rounded-xl px-3 py-2 text-sm font-bold text-forest hover:bg-mist" onClick={() => setOpen(false)}>See all notifications →</Link>
    </div>}
  </div>;
}
