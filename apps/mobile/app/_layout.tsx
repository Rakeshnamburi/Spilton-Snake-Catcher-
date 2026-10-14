import {Stack} from "expo-router";
import {PaperProvider} from "react-native-paper";
import {StatusBar} from "expo-status-bar";
import {theme} from "@/services/theme";
import {LanguageProvider, useI18n} from "@/services/i18n";
import {ReportProvider} from "@/features/report/report-context";
import {MarketplaceProvider} from "@/features/marketplace/context";

function AppStack() {
  const {t} = useI18n();
  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{headerStyle:{backgroundColor:theme.colors.primary},headerTintColor:"white",headerTitleStyle:{fontWeight:"700"}}}>
        <Stack.Screen name="index" options={{headerShown:false}} />
        <Stack.Screen name="onboarding" options={{title:t("navWelcome")}} />
        <Stack.Screen name="home" options={{title:t("navHome")}} />
        <Stack.Screen name="report" options={{title:t("navReport")}} />
        <Stack.Screen name="report-triage" options={{title:t("navTriage")}} />
        <Stack.Screen name="report-location" options={{title:t("navLocation")}} />
        <Stack.Screen name="report-media" options={{title:t("navPhotos")}} />
        <Stack.Screen name="report-reporter" options={{title:t("navReporter")}} />
        <Stack.Screen name="report-review" options={{title:t("navReview")}} />
        <Stack.Screen name="report-confirmation" options={{title:t("navConfirmation"), headerBackVisible:false}} />
        <Stack.Screen name="track" options={{title:t("navTrack")}} />
        <Stack.Screen name="my-reports" options={{title:t("navMyReports")}} />
        <Stack.Screen name="incidents/[id]/index" options={{title:t("navIncident")}} />
        <Stack.Screen name="incidents/[id]/timeline" options={{title:t("navTimeline")}} />
        <Stack.Screen name="safety" options={{title:t("navSafety")}} />
        <Stack.Screen name="emergency" options={{title:t("navEmergency")}} />
        <Stack.Screen name="login" options={{title:t("navLogin")}} />
        <Stack.Screen name="register" options={{title:t("navRegister")}} />
        <Stack.Screen name="profile" options={{title:t("navProfile")}} />
        <Stack.Screen name="nearby-rescuers" options={{title:"Nearby demo rescuers"}} />
        <Stack.Screen name="rescuers/[id]" options={{title:"Demo rescuer profile"}} />
        <Stack.Screen name="marketplace-location" options={{title:"Select location"}} />
        <Stack.Screen name="book/[rescuerId]" options={{title:"Request demo assistance"}} />
        <Stack.Screen name="booking-confirmation" options={{title:"Demo confirmation", headerBackVisible:false}} />
        <Stack.Screen name="bookings" options={{title:"My demo bookings"}} />
        <Stack.Screen name="bookings/[id]" options={{title:"Booking details"}} />
        <Stack.Screen name="rescuer-register" options={{title:"Rescuer application"}} />
        <Stack.Screen name="rescuer-dashboard" options={{title:"Rescuer dashboard"}} />
        <Stack.Screen name="rescuer-bookings" options={{title:"Incoming demo requests"}} />
      </Stack>
    </>
  );
}

export default function Layout() {
  return (
    <PaperProvider theme={theme}>
      <LanguageProvider>
        <ReportProvider>
          <MarketplaceProvider>
            <AppStack />
          </MarketplaceProvider>
        </ReportProvider>
      </LanguageProvider>
    </PaperProvider>
  );
}
