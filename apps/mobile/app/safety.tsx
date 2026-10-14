import {Screen} from "@/components/screen";
import {InfoCard} from "@/components/cards";
export default function Safety(){return <Screen title="Snake safety" subtitle="Identification is never a substitute for distance or medical care.">{["Keep a safe distance and leave an escape route.","Do not touch, trap, provoke, or attempt to capture a snake.","Keep children and pets well away.","Do not attempt rescue yourself; use authorized wildlife assistance.","For suspected snakebite, seek immediate medical care and call 112."].map((x,i)=><InfoCard title={`${i+1}. ${i===4?"Get medical help":"Stay safe"}`} key={x}>{x}</InfoCard>)}</Screen>}

