"use client";

import {useCallback, useEffect, useState} from "react";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";
import {formatDate, humanize} from "@/lib/marketplace";
import type {DemoPayment, DemoReview} from "@spilton/shared-types";

type RescueRow={id:string;booking_reference:string;outcome_label:string;completion_status:string;completed_at:string;evidence_count:number;is_demo:true};
type Dispute={id:string;booking_id:string;reason:string;status:string;resolution_note:string|null;created_at:string;is_demo:true};
type EvidenceRow={id:string;booking_reference:string;original_filename:string;content_type:string;file_size:number;evidence_type:string;retention_expires_at:string;malware_scan_status:string;created_at:string};
type LedgerRow={id:string;transaction_group:string;account_code:string;direction:string;amount:string;currency:string;description:string;created_at:string};

function Notice(){return <div className="rounded-2xl bg-danger p-5 text-sm font-bold text-white">DEMO ADMIN DATA ONLY — no real rescue, charge, transfer, or payout is represented.</div>;}

export function AdminRescueReports(){
 const[data,setData]=useState<RescueRow[]>([]);const[error,setError]=useState("");
 useEffect(()=>{api<RescueRow[]>("/api/v1/admin/rescue-reports").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load reports."));},[]);
 return <div className="space-y-6"><Notice/>{error&&<p className="card text-danger">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Booking</th><th>Outcome</th><th>Confirmation</th><th>Evidence</th><th>Completed</th></tr></thead><tbody>{data.map((item)=><tr className="border-b last:border-0" key={item.id}><td className="py-4 font-bold text-forest">{item.booking_reference}</td><td>{item.outcome_label}</td><td>{humanize(item.completion_status)}</td><td>{item.evidence_count} private file(s)</td><td>{formatDate(item.completed_at)}</td></tr>)}</tbody></table>{!data.length&&!error&&<p className="py-8 text-center text-slate-600">No demo completion reports.</p>}</section></div>;
}

export function AdminPayments(){
 const[data,setData]=useState<DemoPayment[]>([]);const[error,setError]=useState("");
 useEffect(()=>{api<DemoPayment[]>("/api/v1/admin/payments").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load payments."));},[]);
 return <div className="space-y-6"><Notice/>{error&&<p className="card text-danger">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Reference</th><th>Method</th><th>Status</th><th>Gross</th><th>Commission</th><th>Rescuer share</th></tr></thead><tbody>{data.map((item)=><tr className="border-b last:border-0" key={item.id}><td className="py-4 font-bold text-forest">{item.payment_reference}</td><td>{humanize(item.method)}</td><td>{humanize(item.status)}</td><td>₹{item.amount}</td><td>{item.commission_amount?"₹"+item.commission_amount:"—"}</td><td>{item.rescuer_share?"₹"+item.rescuer_share:"—"}</td></tr>)}</tbody></table>{!data.length&&!error&&<p className="py-8 text-center text-slate-600">No demo payments.</p>}<p className="mt-5 text-xs text-danger">All values are illustrative and non-withdrawable.</p></section></div>;
}

export function AdminReviews(){
 const[data,setData]=useState<DemoReview[]>([]);const[error,setError]=useState("");const[busy,setBusy]=useState("");
 const load=useCallback(()=>api<DemoReview[]>("/api/v1/admin/reviews").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load reviews.")),[]);
 useEffect(()=>{void load();},[load]);
 async function moderate(id:string,status:"PUBLISHED_DEMO"|"HIDDEN"|"REMOVED"){setBusy(id);try{await api("/api/v1/admin/reviews/"+id,{method:"PATCH",body:JSON.stringify({status,resolution_note:"Administrator moderation decision."})});await load();}catch(reason){setError(reason instanceof Error?reason.message:"Moderation failed.");}finally{setBusy("");}}
 return <div className="space-y-6"><Notice/>{error&&<p className="card text-danger">{error}</p>}{data.map((item)=><article className="card" key={item.id}><div className="flex flex-wrap justify-between gap-4"><div><p className="eyebrow">{item.rating}/5 · {humanize(item.moderation_status)}</p><p className="mt-3">{item.review_text||"No written comment."}</p><p className="mt-2 text-xs text-slate-500">{formatDate(item.created_at)}</p></div><div className="flex flex-wrap gap-2"><Button disabled={busy===item.id} onClick={()=>void moderate(item.id,"PUBLISHED_DEMO")}>Publish</Button><Button className="bg-amber-700" disabled={busy===item.id} onClick={()=>void moderate(item.id,"HIDDEN")}>Hide</Button><Button className="bg-slate-700" disabled={busy===item.id} onClick={()=>void moderate(item.id,"REMOVED")}>Remove</Button></div></div></article>)}{!data.length&&!error&&<p className="card text-center text-slate-600">No demo reviews.</p>}</div>;
}

export function AdminDisputes(){
 const[data,setData]=useState<Dispute[]>([]);const[error,setError]=useState("");const[busy,setBusy]=useState("");
 const load=useCallback(()=>api<Dispute[]>("/api/v1/admin/disputes").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load disputes.")),[]);
 useEffect(()=>{void load();},[load]);
 async function resolve(id:string){setBusy(id);try{await api("/api/v1/admin/disputes/"+id,{method:"PATCH",body:JSON.stringify({resolution_note:"Reviewed and resolved in the simulated workflow.",restore_completed:true})});await load();}catch(reason){setError(reason instanceof Error?reason.message:"Resolution failed.");}finally{setBusy("");}}
 return <div className="space-y-6"><Notice/>{error&&<p className="card text-danger">{error}</p>}{data.map((item)=><article className="card" key={item.id}><p className="eyebrow">{humanize(item.status)}</p><p className="mt-3 leading-6">{item.reason}</p><p className="mt-2 text-xs text-slate-500">{formatDate(item.created_at)}</p>{item.status==="OPEN"?<Button className="mt-5" disabled={busy===item.id} onClick={()=>void resolve(item.id)}>Resolve demo dispute</Button>:<p className="mt-4 font-bold text-forest">{item.resolution_note}</p>}</article>)}{!data.length&&!error&&<p className="card text-center text-slate-600">No demo completion disputes.</p>}</div>;
}

export function AdminEvidence(){
 const[data,setData]=useState<EvidenceRow[]>([]);const[error,setError]=useState("");
 useEffect(()=>{api<EvidenceRow[]>("/api/v1/admin/evidence").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load evidence."));},[]);
 return <div className="space-y-6"><Notice/>{error&&<p className="card text-danger">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[840px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Booking</th><th>Private object</th><th>Category</th><th>Sanitization</th><th>Retention expiry</th></tr></thead><tbody>{data.map((item)=><tr className="border-b last:border-0" key={item.id}><td className="py-4 font-bold text-forest">{item.booking_reference}</td><td>{item.original_filename}<br/><span className="text-xs text-slate-500">{Math.round(item.file_size/1024)} KB · {item.content_type}</span></td><td>{humanize(item.evidence_type)}</td><td>{humanize(item.malware_scan_status)}</td><td>{formatDate(item.retention_expires_at)}</td></tr>)}</tbody></table>{!data.length&&!error&&<p className="py-8 text-center text-slate-600">No retained private evidence.</p>}<p className="mt-5 text-xs text-slate-500">Exact evidence coordinates and storage keys are intentionally excluded.</p></section></div>;
}

export function AdminLedger(){
 const[data,setData]=useState<LedgerRow[]>([]);const[error,setError]=useState("");
 useEffect(()=>{api<LedgerRow[]>("/api/v1/admin/ledger").then(setData).catch((reason)=>setError(reason instanceof Error?reason.message:"Unable to load ledger."));},[]);
 return <div className="space-y-6"><Notice/>{error&&<p className="card text-danger">{error}</p>}<section className="card overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="py-3">Group</th><th>Account</th><th>Direction</th><th>Amount</th><th>Description</th></tr></thead><tbody>{data.map((item)=><tr className="border-b last:border-0" key={item.id}><td className="py-4 font-mono text-xs">{item.transaction_group}</td><td>{humanize(item.account_code)}</td><td>{item.direction}</td><td>₹{item.amount}</td><td>{item.description}</td></tr>)}</tbody></table>{!data.length&&!error&&<p className="py-8 text-center text-slate-600">No demo ledger entries.</p>}<p className="mt-5 text-xs text-danger">Illustrative double-entry records only; no settlement or withdrawal exists.</p></section></div>;
}
