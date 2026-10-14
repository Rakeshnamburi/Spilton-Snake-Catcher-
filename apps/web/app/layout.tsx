import type {Metadata} from "next";
import "./globals.css";
import {SiteShell} from "@/components/site-shell";
import {LanguageProvider} from "@/lib/i18n";
export const metadata:Metadata={title:{default:"SPILTON Snake Rescue",template:"%s · SPILTON"},description:"Saving Lives. Protecting Wildlife. A demo-mode snake sighting and safety platform."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><LanguageProvider><SiteShell>{children}</SiteShell></LanguageProvider></body></html>}
