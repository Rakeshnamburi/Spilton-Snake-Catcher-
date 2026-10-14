import {AuthForm} from "@/features/auth/auth-form";
export default function Login(){return <section className="bg-mist py-16"><div className="container-page"><div className="mb-8 text-center"><p className="eyebrow">Secure access</p><h1 className="mt-2 text-4xl font-black">Welcome back</h1><p className="mt-3 text-slate-600">Sign in to view only the incidents connected to your account.</p></div><AuthForm mode="login"/></div></section>}

