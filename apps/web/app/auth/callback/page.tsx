"use client";

import Link from "next/link";
import {useRouter, useSearchParams} from "next/navigation";
import {Suspense, useEffect, useState} from "react";
import {api} from "@/lib/api";

function CallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Finishing sign-in…");

  useEffect(() => {
    const status = searchParams.get("status");
    const returnTo = searchParams.get("return_to") || "/track";
    const reason = searchParams.get("reason");

    if (status === "error") {
      setMessage(reason === "provider_not_configured"
        ? "That sign-in provider is not configured yet. Use email and password or the OTP option instead."
        : "We could not complete sign-in. Please try again.");
      return;
    }

    let cancelled = false;
    api("/api/v1/auth/me")
      .then(() => { if (!cancelled) router.replace(returnTo); })
      .catch(() => { if (!cancelled) setMessage("Your session could not be confirmed. Please sign in again."); });
    return () => { cancelled = true; };
  }, [router, searchParams]);

  return <section className="bg-mist py-20">
    <div className="container-page max-w-md text-center">
      <p className="eyebrow">Secure access</p>
      <h1 className="mt-2 text-3xl font-black">Signing you in</h1>
      <p className="mt-4 text-slate-600">{message}</p>
      <p className="mt-6 text-sm"><Link className="font-bold text-forest" href="/login">Back to sign in</Link></p>
    </div>
  </section>;
}

export default function AuthCallback() {
  return <Suspense fallback={<section className="bg-mist py-20"><div className="container-page max-w-md text-center text-slate-600">Finishing sign-in…</div></section>}>
    <CallbackInner/>
  </Suspense>;
}
