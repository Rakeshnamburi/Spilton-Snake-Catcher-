import {Linking} from "react-native";
import {Button} from "react-native-paper";
import {Screen} from "@/components/screen";
import {InfoCard} from "@/components/cards";
export default function Emergency(){return <Screen title="Emergency assistance" subtitle="SPILTON is not a live emergency dispatch service."><InfoCard title="Suspected snakebite" danger>Call 112 and seek immediate medical assistance. Keep the person calm and still. Do not cut, suck, ice, or apply a tourniquet.</InfoCard><Button mode="contained" buttonColor="#DC2626" icon="phone" onPress={()=>Linking.openURL("tel:112")}>Call 112</Button><InfoCard title="Wildlife directory">Only administrator-configured, source-verified public contacts will appear here. This prototype includes no invented numbers.</InfoCard></Screen>}

