"use client";
import Link from "next/link";
import {Languages,Menu,ShieldCheck,X} from "lucide-react";
import {useState} from "react";
import {NotificationBell} from "@/components/notification-bell";
import {LANGUAGES, useI18n, type Language} from "@/lib/i18n";

/** The two actions every visitor needs: find a catcher, or become one. */
const primary=[["nav.findCatcher","/rescuers"],["nav.joinCatcher","/rescuer/register"]];
const secondary=[["nav.bookings","/bookings"],["nav.rescuerDesk","/rescuer/dashboard"],["nav.report","/report"],["nav.safety","/safety"],["nav.emergency","/emergency"]];
const overflow=[["nav.about","/about"],["nav.profile","/profile"]];
const allLinks=[...primary,...secondary,...overflow];

export function SiteShell({children}:{children:React.ReactNode}){
 const [open,setOpen]=useState(false);
 const {language,setLanguage,t,languageLabels}=useI18n();
 return <div className="min-h-screen bg-white">
  <div className="bg-danger px-4 py-2 text-center text-xs font-bold text-white">{t("demo.banner")}</div>
  <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur"><div className="container-page flex h-20 items-center justify-between gap-4">
   <Link href="/" className="flex shrink-0 items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-forest text-white"><ShieldCheck/></span><span><strong className="block text-base tracking-tight text-forest">SPILTON</strong><span className="text-xs text-slate-500">Snake Rescue</span></span></Link>

   <nav className="hidden items-center gap-2 xl:flex" aria-label="Primary navigation">
    <Link className="rounded-xl bg-forest px-4 py-2 text-sm font-bold text-white hover:bg-forest/90" href={primary[0][1]}>{t(primary[0][0])}</Link>
    <Link className="rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest hover:bg-mist" href={primary[1][1]}>{t(primary[1][0])}</Link>
    <span className="mx-1 h-6 w-px bg-slate-200" aria-hidden="true"/>
    {secondary.map(([label,href])=><Link className="text-sm font-semibold text-slate-600 hover:text-forest" href={href} key={href}>{t(label)}</Link>)}
    <span className="mx-1 h-6 w-px bg-slate-200" aria-hidden="true"/>
    <NotificationBell/>
    <label className="flex items-center gap-1 text-slate-600"><Languages size={16}/><span className="sr-only">{t("nav.language")}</span><select className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-xs font-semibold" value={language} onChange={(event)=>setLanguage(event.target.value as Language)}>{LANGUAGES.map(item=><option key={item} value={item}>{languageLabels[item]}</option>)}</select></label>
    <Link className="rounded-xl border border-forest px-4 py-2 text-sm font-bold text-forest" href="/login">{t("nav.signIn")}</Link>
   </nav>

   <div className="flex items-center gap-2 xl:hidden"><NotificationBell/><button aria-label="Toggle menu" onClick={()=>setOpen(!open)}>{open?<X/>:<Menu/>}</button></div>
  </div>

  {open&&<nav className="container-page grid gap-1 pb-5 xl:hidden" aria-label="Mobile navigation">
    <Link className="rounded-xl bg-forest px-4 py-3 text-center font-bold text-white" href={primary[0][1]} onClick={()=>setOpen(false)}>{t(primary[0][0])}</Link>
    <Link className="rounded-xl border border-forest px-4 py-3 text-center font-bold text-forest" href={primary[1][1]} onClick={()=>setOpen(false)}>{t(primary[1][0])}</Link>
    {[...secondary,...overflow].map(([label,href])=><Link className="rounded-lg px-3 py-2 font-semibold hover:bg-mist" href={href} key={href} onClick={()=>setOpen(false)}>{t(label)}</Link>)}
    <Link className="rounded-lg px-3 py-2 font-semibold hover:bg-mist" href="/notifications" onClick={()=>setOpen(false)}>Notifications</Link>
    <label className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold"><Languages size={18}/>{t("nav.language")}<select className="ml-auto rounded-lg border px-2 py-2" value={language} onChange={(event)=>setLanguage(event.target.value as Language)}>{LANGUAGES.map(item=><option key={item} value={item}>{languageLabels[item]}</option>)}</select></label>
    <Link className="rounded-lg px-3 py-2 font-semibold" href="/login">{t("nav.signIn")}</Link>
  </nav>}
  </header>
  <main>{children}</main>
  <footer className="bg-ink py-12 text-slate-300"><div className="container-page grid gap-8 md:grid-cols-3"><div><div className="text-lg font-bold text-white">SPILTON Snake Rescue</div><p className="mt-3 max-w-sm text-sm leading-6">A demo coordination platform designed to connect communities with future verified wildlife partners.</p></div><div><div className="font-bold text-white">Important</div><p className="mt-3 text-sm leading-6">Do not approach, touch, trap, or attempt to identify a snake. Suspected snakebite requires immediate medical care.</p></div><div className="text-sm"><Link href="/about" className="block py-1">Privacy & data use</Link><Link href="/emergency" className="block py-1">Safety disclaimer</Link><p className="mt-4 text-slate-500">© 2026 SPILTON · Demo platform</p></div></div></footer>
 </div>
}
