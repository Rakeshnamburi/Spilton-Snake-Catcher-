import {ButtonHTMLAttributes} from "react";
import {cn} from "@/lib/utils";
export function Button({className,...props}:ButtonHTMLAttributes<HTMLButtonElement>){
  return <button className={cn("inline-flex items-center justify-center gap-2 rounded-xl bg-forest px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald focus:outline-none focus:ring-4 focus:ring-emerald/25 disabled:opacity-50",className)} {...props}/>;
}
