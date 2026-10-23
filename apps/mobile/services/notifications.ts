import {Platform} from "react-native";
import * as Notifications from "expo-notifications";
import {api} from "@/services/api";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

type DeviceResponse={id:string;platform:string;device_label:string|null;token_hint:string;is_active:boolean};

export async function registerDeviceForDemoNotifications():Promise<DeviceResponse>{
  const permission=await Notifications.requestPermissionsAsync();
  if(permission.status!=="granted") throw new Error("Notification permission was denied. In-app updates still work.");
  if(Platform.OS==="android") await Notifications.setNotificationChannelAsync("demo-bookings",{name:"Demo booking updates",importance:Notifications.AndroidImportance.DEFAULT});
  let token:string;
  try{token=(await Notifications.getDevicePushTokenAsync()).data as string;}
  catch{throw new Error("A native push token is unavailable in this build. In-app notifications and polling remain active.");}
  return api<DeviceResponse>("/api/v1/devices/register",{method:"POST",body:JSON.stringify({platform:Platform.OS==="ios"?"IOS":Platform.OS==="android"?"ANDROID":"WEB",token,device_label:"SPILTON mobile app"})});
}

export function addNotificationResponseListener(onBooking:(bookingId:string)=>void){
  return Notifications.addNotificationResponseReceivedListener((response)=>{
    const bookingId=response.notification.request.content.data?.booking_id;
    if(typeof bookingId==="string") onBooking(bookingId);
  });
}
