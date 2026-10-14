import {useRouter} from "expo-router";
import {Button} from "react-native-paper";
import {Screen} from "@/components/screen";
import {InfoCard} from "@/components/cards";
export default function Onboarding(){const router=useRouter();return <Screen title="Safety starts with distance" subtitle="SPILTON helps you record sightings and find trustworthy guidance while the service remains in demo mode."><InfoCard title="Never move closer">A photo and GPS location are optional. Manual location entry always works.</InfoCard><InfoCard title="No live dispatch">No real rescuer is contacted and no operational availability is claimed.</InfoCard><InfoCard title="Snakebite is medical">Call India’s emergency number 112 and seek immediate care.</InfoCard><Button mode="contained" onPress={()=>router.replace("/home")}>Continue safely</Button></Screen>}

