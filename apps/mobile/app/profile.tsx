import {useEffect,useState} from "react";
import {useRouter} from "expo-router";
import {Button,Text} from "react-native-paper";
import {Screen} from "@/components/screen";
import {InfoCard} from "@/components/cards";
import {api,clearToken} from "@/services/api";
type User={name:string;email:string;phone:string;role:string};
export default function Profile(){const router=useRouter();const [user,setUser]=useState<User|null>(null);const [error,setError]=useState("");useEffect(()=>{api<User>("/api/v1/auth/me").then(setUser).catch(e=>setError(e.message))},[]);if(error)return <Screen title="Profile"><InfoCard title="Sign in required">{error}</InfoCard><Button mode="contained" onPress={()=>router.push("/login")}>Sign in</Button></Screen>;return <Screen title="Profile" subtitle="Account details loaded from the shared backend.">{user?<InfoCard title={user.name}>{user.email}{"\n"}{user.phone}{"\n"}Role: {user.role}</InfoCard>:<Text>Loading…</Text>}<Button mode="outlined" onPress={async()=>{await clearToken();router.replace("/home")}}>Sign out</Button></Screen>}

