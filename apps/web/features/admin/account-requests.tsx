"use client";

import {useCallback, useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {api, ApiError} from "@/lib/api";

type RequestItem = {id:string;user_name:string;user_email:string;request_type:string;status:string;reason:string|null;created_at:string;processed_at:string|null};
type Page = {items:RequestItem[];total:number;page:number;limit:number;pages:number};

export function AdminAccountRequests() {
  const [data,setData]=useState<Page|null>(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState("");
  const load=useCallback(async()=>{
    try { setData(await api<Page>("/api/v1/admin/account-requests")); setError(""); }
    catch(reason){setError(reason instanceof ApiError&&(reason.status===401||reason.status===403)?"An administrator account is required.":reason instanceof Error?reason.message:"Unable to load privacy requests.");}
  },[]);
  useEffect(()=>{void load();},[load]);
  async function update(item:RequestItem,status:"UNDER_REVIEW"|"COMPLETED"|"REJECTED"){
    setBusy(item.id);setError("");
    try{await api(`/api/v1/admin/account-requests/${item.id}`,{method:"PATCH",body:JSON.stringify({status,note:`Administrator changed privacy request to ${status}.`})});await load();}
    catch(reason){setError(reason instanceof Error?reason.message:"Unable to update request.");}
    finally{setBusy("");}
  }
  return <div className="space-y-6"><div className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-sm leading-6 text-amber-950"><strong>Manual privacy workflow.</strong> Completing a request records review status only; it does not silently erase relational, legal, safety, or audit records.</div>{error&&<div className="card border-red-200 text-danger" role="alert">{error}</div>}{data&&!data.items.length&&<div className="card text-center text-slate-600">No account data requests.</div>}{data?.items.map(item=><article className="card" key={item.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">{item.request_type}</p><h2 className="mt-2 text-xl font-black">{item.user_name}</h2><p className="mt-1 text-sm text-slate-600">{item.user_email}</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black">{item.status.replaceAll("_"," ")}</span></div>{item.reason&&<p className="mt-5 rounded-xl bg-mist p-4 text-sm">{item.reason}</p>}<p className="mt-4 text-xs text-slate-500">Requested {new Date(item.created_at).toLocaleString()}</p>{!["COMPLETED","REJECTED"].includes(item.status)&&<div className="mt-5 flex flex-wrap gap-3"><Button disabled={busy===item.id} onClick={()=>void update(item,"UNDER_REVIEW")}>Start review</Button><Button disabled={busy===item.id} onClick={()=>void update(item,"COMPLETED")}>Mark completed</Button><Button className="bg-slate-700" disabled={busy===item.id} onClick={()=>void update(item,"REJECTED")}>Reject</Button></div>}</article>)}</div>;
}
