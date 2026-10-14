import {AuthForm} from "@/features/auth/auth-form";
export default function Register(){return <section className="bg-mist py-16"><div className="container-page"><div className="mb-8 text-center"><p className="eyebrow">Citizen registration</p><h1 className="mt-2 text-4xl font-black">Create your account</h1><p className="mt-3 text-slate-600">Public registration always creates a citizen account. Privileged roles require administrator review.</p></div><AuthForm mode="register"/></div></section>}

