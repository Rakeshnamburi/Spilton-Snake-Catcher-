"use client";

import Link from "next/link";
import {useRouter} from "next/navigation";
import {useMemo} from "react";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {z} from "zod";
import {Button} from "@/components/ui/button";
import {api} from "@/lib/api";

type Mode = "login" | "register";
type Values = {name?: string; email: string; phone?: string; password: string};

function makeSchema(mode: Mode): z.ZodType<Values> {
  return z.object({
    name: mode === "register" ? z.string().trim().min(2, "Enter your full name.").max(120) : z.string().optional(),
    email: z.string().trim().email("Enter a valid email address."),
    phone: mode === "register"
      ? z.string().regex(/^\+?[0-9]{10,15}$/, "Enter 10–15 digits, optionally beginning with +.")
      : z.string().optional(),
    password: mode === "register"
      ? z.string().min(10, "Use at least 10 characters.").max(128)
      : z.string().min(1, "Enter your password.").max(128),
  });
}

export function AuthForm({mode}: {mode: Mode}) {
  const router = useRouter();
  const schema = useMemo(() => makeSchema(mode), [mode]);
  const {register, handleSubmit, formState: {errors, isSubmitting}, setError} = useForm<Values>({resolver: zodResolver(schema)});

  async function submit(values: Values) {
    try {
      await api(`/api/v1/auth/${mode}`, {method: "POST", body: JSON.stringify(values)});
      router.push(mode === "login" ? "/track" : "/report");
    } catch (reason) {
      setError("root", {message: reason instanceof Error ? reason.message : "Unable to continue."});
    }
  }

  return <form onSubmit={handleSubmit(submit)} className="card mx-auto max-w-lg space-y-5" noValidate>
    {mode === "register" && <>
      <label className="block"><span className="label">Full name</span><input className="field" autoComplete="name" {...register("name")}/>{errors.name && <small className="text-danger">{errors.name.message}</small>}</label>
      <label className="block"><span className="label">Phone</span><input className="field" type="tel" inputMode="tel" autoComplete="tel" {...register("phone")}/>{errors.phone && <small className="text-danger">{errors.phone.message}</small>}</label>
    </>}
    <label className="block"><span className="label">Email</span><input className="field" type="email" autoComplete="email" {...register("email")}/><small className="text-danger">{errors.email?.message}</small></label>
    <label className="block"><span className="label">Password</span><input className="field" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} {...register("password")}/><small className="text-danger">{errors.password?.message}</small></label>
    {errors.root && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-danger">{errors.root.message}</p>}
    <Button className="w-full" disabled={isSubmitting}>{isSubmitting ? "Please wait…" : mode === "login" ? "Sign in securely" : "Create citizen account"}</Button>
    <p className="text-center text-sm text-slate-600">{mode === "login" ? "New to SPILTON? " : "Already registered? "}<Link className="font-bold text-forest" href={mode === "login" ? "/register" : "/login"}>{mode === "login" ? "Create an account" : "Sign in"}</Link></p>
  </form>;
}
