import * as SecureStore from "expo-secure-store";
import {createContext, ReactNode, useContext, useEffect, useMemo, useState} from "react";

export const LANGUAGES = [
  {code: "en", label: "English"},
  {code: "te", label: "తెలుగు"},
  {code: "ta", label: "தமிழ்"},
  {code: "kn", label: "ಕನ್ನಡ"},
  {code: "ml", label: "മലയാളം"},
] as const;

export type Locale = typeof LANGUAGES[number]["code"];

const ENGLISH = {
  demoBanner: "DEMO PLATFORM · NOT AN ACTIVE EMERGENCY RESCUE SERVICE · MEDICAL EMERGENCY: 112",
  navWelcome: "Welcome",
  navHome: "SPILTON",
  navReport: "Report sighting",
  navTriage: "Safety triage",
  navLocation: "Select location",
  navPhotos: "Optional photos",
  navReporter: "Reporter details",
  navReview: "Review report",
  navConfirmation: "Submission confirmation",
  navTrack: "Track incident",
  navMyReports: "My reports",
  navIncident: "Incident details",
  navTimeline: "Status timeline",
  navSafety: "Safety",
  navEmergency: "Emergency",
  navLogin: "Sign in",
  navRegister: "Register",
  navProfile: "Profile",
  navNearby: "Nearby demo rescuers",
  navRescuerProfile: "Demo rescuer profile",
  navMarketplaceLocation: "Select location",
  navBook: "Request demo assistance",
  navBookingConfirmation: "Demo confirmation",
  navBookings: "My demo bookings",
  navBookingDetails: "Booking details",
  navTracking: "Demo live tracking",
  profileSubtitle: "Account details loaded from the protected shared backend.",
  profileSignInRequired: "Sign in required",
  profileLoading: "Loading protected profile…",
  profileName: "Full name",
  profilePhone: "Phone",
  profileEmail: "Email",
  profileCurrentPassword: "Current password",
  profileSave: "Save profile",
  profileSaved: "Profile updated securely.",
  profileExport: "Request data export",
  profileDelete: "Request account deletion",
  profileRequestRecorded: "Privacy request recorded for administrator review.",
  profileSignOut: "Sign out everywhere",
  marketplaceSearch: "Search protected directory",
  marketplaceNoRescuer: "No eligible demo rescuer available",
  marketplaceEmergency: "Open emergency information",
  marketplaceProfile: "Profile",
  marketplaceRequest: "Request",
  bookingLoading: "Loading protected bookings…",
  bookingNone: "No demo bookings",
  bookingBrowse: "Browse demo profiles",
  bookingView: "View details",
  homeTitle: "What do you need?",
  homeSubtitle: "Emergency medical help must not wait for this app.",
  reportAction: "Report snake sighting",
  reportsAction: "View my reports",
  trackAction: "Find report by reference",
  safetyAction: "Snake safety",
  emergencyAction: "Emergency information",
  language: "Language",
  incidentTitle: "Incident information",
  incidentSubtitle: "Step 1 of 6 · Stay at a safe distance while entering what you observed.",
  description: "Sighting description",
  sightingTime: "Date and time of sighting",
  triageTitle: "Safety triage",
  bittenQuestion: "Is anyone bitten or injured?",
  visibleQuestion: "Is the snake currently visible?",
  dangerQuestion: "Is anyone in immediate danger?",
  yes: "Yes",
  no: "No",
  continueTriage: "Continue to safety triage",
  continueLocation: "Continue to location",
  medicalTitle: "Do not wait to submit this form",
  medicalGuidance: "Call 112 and seek immediate medical care now. A demo report is not a substitute for emergency medical assistance.",
  call112: "Call 112",
  criticalTranslationReview: "Critical medical translations require human safety review; the English instruction is shown as the authoritative fallback.",
  locationTitle: "Sighting location",
  locationSubtitle: "Step 3 of 6 · GPS is optional. Manual entry always works.",
  chooseState: "Choose state",
  chooseDistrict: "Choose district",
  city: "City or village",
  landmark: "Landmark (optional)",
  addressDescription: "Address description (optional)",
  latitude: "Latitude (optional)",
  longitude: "Longitude (optional)",
  accuracy: "Accuracy in metres (optional)",
  useLocation: "Use my current location",
  refreshLocation: "Refresh location",
  locating: "Getting location…",
  locationSuccess: "Location captured. Review the coordinates before continuing.",
  locationDenied: "Location permission was denied. Enter the locality manually; GPS is never required.",
  locationTimeout: "Location request timed out. Retry or use manual entry.",
  locationError: "Location is unavailable. Retry or use manual entry.",
  confirmLocation: "I reviewed this location and locality information.",
  continuePhotos: "Continue to optional photos",
  mapUnavailableTitle: "Coordinate selection available",
  mapUnavailable: "The current managed Expo build has no native map module configured. GPS and manual coordinates remain fully functional.",
  photosTitle: "Optional sighting photos",
  photosSubtitle: "Step 4 of 6 · Add up to 3 images, each no larger than 5 MB.",
  photoSafety: "Never move closer to the snake to take a photo. Photos are not required.",
  choosePhotos: "Choose photos",
  addMorePhotos: "Add more photos",
  remove: "Remove",
  photoPermissionDenied: "Photo access was denied. Continue without photos or change permission in device settings.",
  photoInvalid: "Only JPEG, PNG, and WebP images up to 5 MB are accepted.",
  continueReporter: "Continue to reporter details",
  reporterTitle: "Reporter details",
  reporterSubtitle: "Step 5 of 6 · These details remain private and are only available to authorized users.",
  reporterName: "Name",
  contactPhone: "Contact number",
  reporterEmail: "Email (optional)",
  consent: "I understand this creates a demo incident and does not dispatch real rescue help.",
  continueReview: "Review demo report",
  reviewTitle: "Review demo report",
  reviewSubtitle: "Step 6 of 6 · Check every section before submitting.",
  edit: "Edit",
  submit: "Submit demo incident",
  submitting: "Submitting securely…",
  duplicatePrevented: "This report may already have been submitted. Check My Reports before trying again.",
  uploadRetryTitle: "Report saved; some photos were not uploaded",
  retryUploads: "Retry failed uploads",
  continueWithoutPhotos: "Continue without failed photos",
  confirmationTitle: "Demo report saved",
  confirmationMessage: "Your report is stored in the demo system. No real rescuer has been contacted or dispatched.",
  reference: "Reference",
  viewReport: "View report",
  createAnother: "Create another report",
  myReportsTitle: "My reports",
  myReportsSubtitle: "Only reports belonging to your signed-in account are shown.",
  noReports: "No demo reports found.",
  retry: "Retry",
  loadMore: "Load more",
  signIn: "Sign in",
  timeline: "Status timeline",
  cancelReport: "Cancel eligible report",
  cancelConfirmTitle: "Cancel this demo report?",
  cancelConfirmBody: "This records a cancellation event and cannot be undone.",
  keepReport: "Keep report",
  cancel: "Cancel report",
  media: "Submitted media",
  noMedia: "No photos were submitted.",
  details: "Incident summary",
  location: "Location",
  demoOnly: "Demo only — no live dispatch.",
  sessionExpired: "Your session expired. Sign in again to continue.",
  networkError: "Cannot reach the server. Check your connection and try again.",
  timeoutError: "The server took too long to respond. Try again.",
  genericError: "Something went wrong. Try again.",
  statusCREATED: "Created",
  statusUNDER_REVIEW: "Under review",
  statusASSIGNED: "Assigned (simulated)",
  statusIN_PROGRESS: "In progress (simulated)",
  statusRESOLVED: "Resolved",
  statusCLOSED: "Closed",
  statusCANCELLED: "Cancelled",
  statusUNABLE_TO_ASSIST: "Unable to assist",
  safetyTitle: "Snake safety",
  safetySubtitle: "Identification is never a substitute for distance or medical care.",
  safetyDistance: "Keep a safe distance and leave an escape route.",
  safetyDoNotTouch: "Do not touch, trap, provoke, catch, or relocate a snake.",
  safetyChildren: "Keep children and pets well away.",
  safetyNoRescue: "Do not attempt rescue yourself; use authorized wildlife assistance.",
  safetyMedical: "For suspected snakebite, seek immediate medical care and call 112.",
} as const;

export type TranslationKey = keyof typeof ENGLISH;
type Dictionary = Partial<Record<TranslationKey, string>>;

const translations: Record<Locale, Dictionary> = {
  en: ENGLISH,
  te: {
    navHome: "SPILTON", navReport: "పాము కనిపించినట్లు నివేదించండి", navLocation: "స్థలాన్ని ఎంచుకోండి", navProfile: "ప్రొఫైల్", navNearby: "సమీప డెమో రక్షకులు", navRescuerProfile: "డెమో రక్షకుడి ప్రొఫైల్", navMarketplaceLocation: "స్థానం ఎంచుకోండి", navBook: "డెమో సహాయం కోరండి", navBookingConfirmation: "డెమో నిర్ధారణ", navBookings: "నా డెమో బుకింగ్‌లు", navBookingDetails: "బుకింగ్ వివరాలు", navTracking: "డెమో లైవ్ ట్రాకింగ్",
    profileSubtitle: "సురక్షిత షేర్డ్ బ్యాకెండ్ నుండి ఖాతా వివరాలు.", profileSignInRequired: "సైన్ ఇన్ అవసరం", profileLoading: "సురక్షిత ప్రొఫైల్ లోడ్ అవుతోంది…", profileName: "పూర్తి పేరు", profilePhone: "ఫోన్", profileEmail: "ఇమెయిల్", profileCurrentPassword: "ప్రస్తుత పాస్‌వర్డ్", profileSave: "ప్రొఫైల్ సేవ్ చేయండి", profileSaved: "ప్రొఫైల్ సురక్షితంగా నవీకరించబడింది.", profileExport: "డేటా ఎగుమతి కోరండి", profileDelete: "ఖాతా తొలగింపు కోరండి", profileRequestRecorded: "గోప్యత అభ్యర్థన నిర్వాహక సమీక్ష కోసం నమోదైంది.", profileSignOut: "అన్ని చోట్ల సైన్ అవుట్", marketplaceSearch: "సురక్షిత డైరెక్టరీని వెతకండి", marketplaceNoRescuer: "అర్హత గల డెమో రక్షకుడు లేరు", marketplaceEmergency: "అత్యవసర సమాచారం తెరవండి", marketplaceProfile: "ప్రొఫైల్", marketplaceRequest: "అభ్యర్థించండి", bookingLoading: "సురక్షిత బుకింగ్‌లు లోడ్ అవుతున్నాయి…", bookingNone: "డెమో బుకింగ్‌లు లేవు", bookingBrowse: "డెమో ప్రొఫైల్‌లను చూడండి", bookingView: "వివరాలు చూడండి",
    navPhotos: "ఐచ్ఛిక ఫోటోలు", navReporter: "నివేదించే వారి వివరాలు", navReview: "నివేదికను పరిశీలించండి",
    navConfirmation: "సమర్పణ నిర్ధారణ", navTrack: "నివేదికను వెతకండి", navMyReports: "నా నివేదికలు",
    navIncident: "సంఘటన వివరాలు", navTimeline: "స్థితి కాలక్రమం", navSafety: "భద్రత", navEmergency: "అత్యవసరం",
    reportAction: "పాము కనిపించినట్లు నివేదించండి", reportsAction: "నా నివేదికలను చూడండి", safetyAction: "పాము భద్రత",
    emergencyAction: "అత్యవసర సమాచారం", language: "భాష", description: "కనిపించిన వివరాలు", sightingTime: "కనిపించిన తేదీ మరియు సమయం",
    triageTitle: "భద్రతా అంచనా", bittenQuestion: "ఎవరైనా కాటుకు గురయ్యారా లేదా గాయపడ్డారా?", visibleQuestion: "పాము ఇప్పుడు కనిపిస్తోందా?",
    dangerQuestion: "ఎవరైనా తక్షణ ప్రమాదంలో ఉన్నారా?", yes: "అవును", no: "కాదు", call112: "112కు కాల్ చేయండి",
    chooseState: "రాష్ట్రాన్ని ఎంచుకోండి", chooseDistrict: "జిల్లాను ఎంచుకోండి", city: "నగరం లేదా గ్రామం", landmark: "గుర్తించదగిన ప్రదేశం (ఐచ్ఛికం)",
    useLocation: "నా ప్రస్తుత స్థానాన్ని ఉపయోగించండి", refreshLocation: "స్థానాన్ని నవీకరించండి", locationDenied: "స్థాన అనుమతి నిరాకరించబడింది. ప్రాంతాన్ని చేతితో నమోదు చేయండి.",
    photoSafety: "ఫోటో కోసం పాముకు దగ్గరగా వెళ్లవద్దు. ఫోటోలు అవసరం లేదు.", choosePhotos: "ఫోటోలను ఎంచుకోండి", remove: "తొలగించండి",
    reporterName: "పేరు", contactPhone: "సంప్రదింపు నంబర్", reporterEmail: "ఇమెయిల్ (ఐచ్ఛికం)", submit: "డెమో సంఘటనను సమర్పించండి",
    confirmationTitle: "డెమో నివేదిక సేవ్ చేయబడింది", reference: "రిఫరెన్స్", myReportsTitle: "నా నివేదికలు", noReports: "డెమో నివేదికలు లేవు.", retry: "మళ్లీ ప్రయత్నించండి",
    statusCREATED: "సృష్టించబడింది", statusUNDER_REVIEW: "పరిశీలనలో ఉంది", statusASSIGNED: "కేటాయించబడింది (అనుకరణ)", statusIN_PROGRESS: "పురోగతిలో ఉంది (అనుకరణ)",
    statusRESOLVED: "పరిష్కరించబడింది", statusCLOSED: "మూసివేయబడింది", statusCANCELLED: "రద్దు చేయబడింది", statusUNABLE_TO_ASSIST: "సహాయం చేయడం సాధ్యం కాలేదు",
    safetyTitle: "పాము భద్రత", safetyDistance: "సురక్షిత దూరం పాటించి, పాము వెళ్లేందుకు దారి వదలండి.", safetyDoNotTouch: "పామును తాకవద్దు, బంధించవద్దు లేదా రెచ్చగొట్టవద్దు.",
    safetyChildren: "పిల్లలు మరియు పెంపుడు జంతువులను దూరంగా ఉంచండి.", safetyNoRescue: "మీరే రక్షించడానికి ప్రయత్నించవద్దు.", safetyMedical: "పాముకాటు అనుమానం ఉంటే వెంటనే వైద్య సహాయం పొందండి మరియు 112కు కాల్ చేయండి.",
  },
  ta: {
    navHome: "SPILTON", navReport: "பாம்பு கண்டதைப் புகாரளிக்கவும்", navLocation: "இடத்தைத் தேர்ந்தெடுக்கவும்", navPhotos: "விருப்பப் படங்கள்", navProfile: "சுயவிவரம்", navNearby: "அருகிலுள்ள டெமோ மீட்பாளர்கள்", navRescuerProfile: "டெமோ மீட்பாளர் சுயவிவரம்", navMarketplaceLocation: "இடத்தைத் தேர்ந்தெடுக்கவும்", navBook: "டெமோ உதவி கோருக", navBookingConfirmation: "டெமோ உறுதி", navBookings: "என் டெமோ முன்பதிவுகள்", navBookingDetails: "முன்பதிவு விவரங்கள்", navTracking: "டெமோ நேரடி கண்காணிப்பு",
    profileSubtitle: "பாதுகாக்கப்பட்ட பகிரப்பட்ட பின்தளத்திலிருந்து கணக்கு விவரங்கள்.", profileSignInRequired: "உள்நுழைவு தேவை", profileLoading: "பாதுகாக்கப்பட்ட சுயவிவரம் ஏற்றப்படுகிறது…", profileName: "முழுப் பெயர்", profilePhone: "தொலைபேசி", profileEmail: "மின்னஞ்சல்", profileCurrentPassword: "தற்போதைய கடவுச்சொல்", profileSave: "சுயவிவரத்தை சேமி", profileSaved: "சுயவிவரம் பாதுகாப்பாக புதுப்பிக்கப்பட்டது.", profileExport: "தரவு ஏற்றுமதி கோருக", profileDelete: "கணக்கு நீக்கம் கோருக", profileRequestRecorded: "தனியுரிமை கோரிக்கை நிர்வாகி ஆய்வுக்காக பதிவு செய்யப்பட்டது.", profileSignOut: "எங்கும் வெளியேறு", marketplaceSearch: "பாதுகாக்கப்பட்ட பட்டியலைத் தேடு", marketplaceNoRescuer: "தகுதியான டெமோ மீட்பாளர் இல்லை", marketplaceEmergency: "அவசர தகவலைத் திற", marketplaceProfile: "சுயவிவரம்", marketplaceRequest: "கோருக", bookingLoading: "பாதுகாக்கப்பட்ட முன்பதிவுகள் ஏற்றப்படுகின்றன…", bookingNone: "டெமோ முன்பதிவுகள் இல்லை", bookingBrowse: "டெமோ சுயவிவரங்களைப் பார்வையிடு", bookingView: "விவரங்களைக் காண்க",
    navReporter: "புகாரளிப்பவர் விவரங்கள்", navReview: "புகாரை மதிப்பாய்வு செய்க", navConfirmation: "சமர்ப்பிப்பு உறுதி", navTrack: "புகாரைத் தேடுக",
    navMyReports: "என் புகார்கள்", navIncident: "சம்பவ விவரங்கள்", navTimeline: "நிலை காலவரிசை", navSafety: "பாதுகாப்பு", navEmergency: "அவசரம்",
    reportAction: "பாம்பு கண்டதைப் புகாரளிக்கவும்", reportsAction: "என் புகார்களைப் பார்க்கவும்", safetyAction: "பாம்பு பாதுகாப்பு", emergencyAction: "அவசர தகவல்",
    language: "மொழி", description: "கண்ட விவரம்", sightingTime: "கண்ட தேதி மற்றும் நேரம்", triageTitle: "பாதுகாப்பு மதிப்பீடு",
    bittenQuestion: "யாராவது கடிக்கப்பட்டாரா அல்லது காயமடைந்தாரா?", visibleQuestion: "பாம்பு தற்போது தெரிகிறதா?", dangerQuestion: "யாராவது உடனடி ஆபத்தில் உள்ளாரா?",
    yes: "ஆம்", no: "இல்லை", call112: "112-ஐ அழைக்கவும்", chooseState: "மாநிலத்தைத் தேர்ந்தெடுக்கவும்", chooseDistrict: "மாவட்டத்தைத் தேர்ந்தெடுக்கவும்", city: "நகரம் அல்லது கிராமம்",
    useLocation: "என் தற்போதைய இடத்தைப் பயன்படுத்து", refreshLocation: "இடத்தைப் புதுப்பி", photoSafety: "படம் எடுக்க பாம்பை நெருங்காதீர்கள். படங்கள் தேவையில்லை.",
    choosePhotos: "படங்களைத் தேர்ந்தெடுக்கவும்", remove: "நீக்கு", reporterName: "பெயர்", contactPhone: "தொடர்பு எண்", reporterEmail: "மின்னஞ்சல் (விருப்பம்)", submit: "டெமோ சம்பவத்தைச் சமர்ப்பிக்கவும்",
    confirmationTitle: "டெமோ புகார் சேமிக்கப்பட்டது", reference: "குறிப்பு", myReportsTitle: "என் புகார்கள்", noReports: "டெமோ புகார்கள் இல்லை.", retry: "மீண்டும் முயற்சி",
    statusCREATED: "உருவாக்கப்பட்டது", statusUNDER_REVIEW: "மதிப்பாய்வில்", statusASSIGNED: "ஒதுக்கப்பட்டது (உருவகப்படுத்தப்பட்டது)", statusIN_PROGRESS: "செயல்பாட்டில் (உருவகப்படுத்தப்பட்டது)",
    statusRESOLVED: "தீர்க்கப்பட்டது", statusCLOSED: "மூடப்பட்டது", statusCANCELLED: "ரத்து செய்யப்பட்டது", statusUNABLE_TO_ASSIST: "உதவ இயலவில்லை",
    safetyTitle: "பாம்பு பாதுகாப்பு", safetyDistance: "பாதுகாப்பான தூரத்தில் இருந்து பாம்பு செல்ல வழிவிடுங்கள்.", safetyDoNotTouch: "பாம்பைத் தொடவோ, பிடிக்கவோ, தூண்டவோ வேண்டாம்.",
    safetyChildren: "குழந்தைகளையும் செல்லப்பிராணிகளையும் விலக்கி வைக்கவும்.", safetyNoRescue: "நீங்களே மீட்க முயற்சிக்காதீர்கள்.", safetyMedical: "பாம்புக்கடி சந்தேகம் இருந்தால் உடனடியாக மருத்துவ உதவி பெற்று 112-ஐ அழைக்கவும்.",
  },
  kn: {
    navHome: "SPILTON", navReport: "ಹಾವು ಕಂಡಿದ್ದನ್ನು ವರದಿ ಮಾಡಿ", navLocation: "ಸ್ಥಳ ಆಯ್ಕೆಮಾಡಿ", navPhotos: "ಐಚ್ಛಿಕ ಚಿತ್ರಗಳು", navProfile: "ಪ್ರೊಫೈಲ್", navNearby: "ಹತ್ತಿರದ ಡೆಮೊ ರಕ್ಷಕರು", navRescuerProfile: "ಡೆಮೊ ರಕ್ಷಕ ಪ್ರೊಫೈಲ್", navMarketplaceLocation: "ಸ್ಥಳ ಆಯ್ಕೆಮಾಡಿ", navBook: "ಡೆಮೊ ನೆರವು ವಿನಂತಿಸಿ", navBookingConfirmation: "ಡೆಮೊ ದೃಢೀಕರಣ", navBookings: "ನನ್ನ ಡೆಮೊ ಬುಕ್ಕಿಂಗ್‌ಗಳು", navBookingDetails: "ಬುಕ್ಕಿಂಗ್ ವಿವರಗಳು", navTracking: "ಡೆಮೊ ಲೈವ್ ಟ್ರ್ಯಾಕಿಂಗ್",
    profileSubtitle: "ಸುರಕ್ಷಿತ ಹಂಚಿದ ಬ್ಯಾಕೆಂಡ್‌ನಿಂದ ಖಾತೆ ವಿವರಗಳು.", profileSignInRequired: "ಸೈನ್ ಇನ್ ಅಗತ್ಯ", profileLoading: "ಸುರಕ್ಷಿತ ಪ್ರೊಫೈಲ್ ಲೋಡ್ ಆಗುತ್ತಿದೆ…", profileName: "ಪೂರ್ಣ ಹೆಸರು", profilePhone: "ಫೋನ್", profileEmail: "ಇಮೇಲ್", profileCurrentPassword: "ಪ್ರಸ್ತುತ ಪಾಸ್‌ವರ್ಡ್", profileSave: "ಪ್ರೊಫೈಲ್ ಉಳಿಸಿ", profileSaved: "ಪ್ರೊಫೈಲ್ ಸುರಕ್ಷಿತವಾಗಿ ನವೀಕರಿಸಲಾಗಿದೆ.", profileExport: "ಡೇಟಾ ರಫ್ತು ವಿನಂತಿಸಿ", profileDelete: "ಖಾತೆ ಅಳಿಸುವಿಕೆ ವಿನಂತಿಸಿ", profileRequestRecorded: "ಗೌಪ್ಯತಾ ವಿನಂತಿ ನಿರ್ವಾಹಕ ಪರಿಶೀಲನೆಗಾಗಿ ದಾಖಲಾಗಿದೆ.", profileSignOut: "ಎಲ್ಲೆಡೆ ಸೈನ್ ಔಟ್", marketplaceSearch: "ಸುರಕ್ಷಿತ ಡೈರೆಕ್ಟರಿ ಹುಡುಕಿ", marketplaceNoRescuer: "ಅರ್ಹ ಡೆಮೊ ರಕ್ಷಕರು ಲಭ್ಯವಿಲ್ಲ", marketplaceEmergency: "ತುರ್ತು ಮಾಹಿತಿ ತೆರೆಯಿರಿ", marketplaceProfile: "ಪ್ರೊಫೈಲ್", marketplaceRequest: "ವಿನಂತಿಸಿ", bookingLoading: "ಸುರಕ್ಷಿತ ಬುಕ್ಕಿಂಗ್‌ಗಳು ಲೋಡ್ ಆಗುತ್ತಿವೆ…", bookingNone: "ಡೆಮೊ ಬುಕ್ಕಿಂಗ್‌ಗಳಿಲ್ಲ", bookingBrowse: "ಡೆಮೊ ಪ್ರೊಫೈಲ್‌ಗಳನ್ನು ನೋಡಿ", bookingView: "ವಿವರಗಳನ್ನು ನೋಡಿ",
    navReporter: "ವರದಿದಾರರ ವಿವರಗಳು", navReview: "ವರದಿ ಪರಿಶೀಲಿಸಿ", navConfirmation: "ಸಲ್ಲಿಕೆ ದೃಢೀಕರಣ", navTrack: "ವರದಿ ಹುಡುಕಿ", navMyReports: "ನನ್ನ ವರದಿಗಳು",
    navIncident: "ಘಟನೆಯ ವಿವರಗಳು", navTimeline: "ಸ್ಥಿತಿ ಕಾಲರೇಖೆ", navSafety: "ಸುರಕ್ಷತೆ", navEmergency: "ತುರ್ತು", reportAction: "ಹಾವು ಕಂಡಿದ್ದನ್ನು ವರದಿ ಮಾಡಿ",
    reportsAction: "ನನ್ನ ವರದಿಗಳನ್ನು ನೋಡಿ", safetyAction: "ಹಾವು ಸುರಕ್ಷತೆ", emergencyAction: "ತುರ್ತು ಮಾಹಿತಿ", language: "ಭಾಷೆ", description: "ಕಂಡ ವಿವರ",
    sightingTime: "ಕಂಡ ದಿನಾಂಕ ಮತ್ತು ಸಮಯ", triageTitle: "ಸುರಕ್ಷತಾ ಮೌಲ್ಯಮಾಪನ", bittenQuestion: "ಯಾರಿಗಾದರೂ ಕಚ್ಚಿದೆಯೇ ಅಥವಾ ಗಾಯವಾಗಿದೆಯೇ?", visibleQuestion: "ಹಾವು ಈಗ ಕಾಣಿಸುತ್ತಿದೆಯೇ?",
    dangerQuestion: "ಯಾರಾದರೂ ತಕ್ಷಣದ ಅಪಾಯದಲ್ಲಿದ್ದಾರೆಯೇ?", yes: "ಹೌದು", no: "ಇಲ್ಲ", call112: "112ಕ್ಕೆ ಕರೆ ಮಾಡಿ", chooseState: "ರಾಜ್ಯ ಆಯ್ಕೆಮಾಡಿ", chooseDistrict: "ಜಿಲ್ಲೆ ಆಯ್ಕೆಮಾಡಿ",
    city: "ನಗರ ಅಥವಾ ಗ್ರಾಮ", useLocation: "ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳ ಬಳಸಿ", refreshLocation: "ಸ್ಥಳ ನವೀಕರಿಸಿ", photoSafety: "ಚಿತ್ರಕ್ಕಾಗಿ ಹಾವಿನ ಹತ್ತಿರ ಹೋಗಬೇಡಿ. ಚಿತ್ರಗಳು ಅಗತ್ಯವಿಲ್ಲ.",
    choosePhotos: "ಚಿತ್ರಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ", remove: "ತೆಗೆದುಹಾಕಿ", reporterName: "ಹೆಸರು", contactPhone: "ಸಂಪರ್ಕ ಸಂಖ್ಯೆ", reporterEmail: "ಇಮೇಲ್ (ಐಚ್ಛಿಕ)", submit: "ಡೆಮೊ ಘಟನೆ ಸಲ್ಲಿಸಿ",
    confirmationTitle: "ಡೆಮೊ ವರದಿ ಉಳಿಸಲಾಗಿದೆ", reference: "ಉಲ್ಲೇಖ", myReportsTitle: "ನನ್ನ ವರದಿಗಳು", noReports: "ಡೆಮೊ ವರದಿಗಳು ಕಂಡುಬಂದಿಲ್ಲ.", retry: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
    statusCREATED: "ರಚಿಸಲಾಗಿದೆ", statusUNDER_REVIEW: "ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ", statusASSIGNED: "ನಿಯೋಜಿಸಲಾಗಿದೆ (ಅನುಕರಣೆ)", statusIN_PROGRESS: "ಪ್ರಗತಿಯಲ್ಲಿದೆ (ಅನುಕರಣೆ)",
    statusRESOLVED: "ಪರಿಹರಿಸಲಾಗಿದೆ", statusCLOSED: "ಮುಚ್ಚಲಾಗಿದೆ", statusCANCELLED: "ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ", statusUNABLE_TO_ASSIST: "ಸಹಾಯ ಮಾಡಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ",
    safetyTitle: "ಹಾವು ಸುರಕ್ಷತೆ", safetyDistance: "ಸುರಕ್ಷಿತ ಅಂತರ ಕಾಯ್ದುಕೊಂಡು ಹಾವು ಹೋಗಲು ದಾರಿ ಬಿಡಿ.", safetyDoNotTouch: "ಹಾವನ್ನು ಮುಟ್ಟಬೇಡಿ, ಹಿಡಿಯಬೇಡಿ ಅಥವಾ ಕೆಣಕಬೇಡಿ.",
    safetyChildren: "ಮಕ್ಕಳು ಮತ್ತು ಸಾಕುಪ್ರಾಣಿಗಳನ್ನು ದೂರವಿಡಿ.", safetyNoRescue: "ನೀವೇ ರಕ್ಷಿಸಲು ಪ್ರಯತ್ನಿಸಬೇಡಿ.", safetyMedical: "ಹಾವು ಕಚ್ಚಿದ ಶಂಕೆಯಿದ್ದರೆ ತಕ್ಷಣ ವೈದ್ಯಕೀಯ ಸಹಾಯ ಪಡೆದು 112ಕ್ಕೆ ಕರೆ ಮಾಡಿ.",
  },
  ml: {
    navHome: "SPILTON", navReport: "പാമ്പിനെ കണ്ടത് റിപ്പോർട്ട് ചെയ്യുക", navLocation: "സ്ഥലം തിരഞ്ഞെടുക്കുക", navPhotos: "ഐച്ഛിക ചിത്രങ്ങൾ", navProfile: "പ്രൊഫൈൽ", navNearby: "സമീപത്തെ ഡെമോ രക്ഷാപ്രവർത്തകർ", navRescuerProfile: "ഡെമോ രക്ഷാപ്രവർത്തക പ്രൊഫൈൽ", navMarketplaceLocation: "സ്ഥലം തിരഞ്ഞെടുക്കുക", navBook: "ഡെമോ സഹായം അഭ്യർത്ഥിക്കുക", navBookingConfirmation: "ഡെമോ സ്ഥിരീകരണം", navBookings: "എന്റെ ഡെമോ ബുക്കിംഗുകൾ", navBookingDetails: "ബുക്കിംഗ് വിവരങ്ങൾ", navTracking: "ഡെമോ തത്സമയ ട്രാക്കിംഗ്",
    profileSubtitle: "സുരക്ഷിത പങ്കിട്ട ബാക്കെൻഡിൽ നിന്നുള്ള അക്കൗണ്ട് വിവരങ്ങൾ.", profileSignInRequired: "സൈൻ ഇൻ ആവശ്യമാണ്", profileLoading: "സുരക്ഷിത പ്രൊഫൈൽ ലോഡ് ചെയ്യുന്നു…", profileName: "പൂർണ്ണ പേര്", profilePhone: "ഫോൺ", profileEmail: "ഇമെയിൽ", profileCurrentPassword: "നിലവിലെ പാസ്‌വേഡ്", profileSave: "പ്രൊഫൈൽ സൂക്ഷിക്കുക", profileSaved: "പ്രൊഫൈൽ സുരക്ഷിതമായി പുതുക്കി.", profileExport: "ഡാറ്റ എക്സ്പോർട്ട് ആവശ്യപ്പെടുക", profileDelete: "അക്കൗണ്ട് ഇല്ലാതാക്കൽ ആവശ്യപ്പെടുക", profileRequestRecorded: "സ്വകാര്യത അഭ്യർത്ഥന അഡ്മിൻ പരിശോധനയ്ക്കായി രേഖപ്പെടുത്തി.", profileSignOut: "എല്ലായിടത്തുനിന്നും സൈൻ ഔട്ട്", marketplaceSearch: "സുരക്ഷിത ഡയറക്ടറി തിരയുക", marketplaceNoRescuer: "യോഗ്യമായ ഡെമോ രക്ഷാപ്രവർത്തകൻ ലഭ്യമല്ല", marketplaceEmergency: "അടിയന്തര വിവരം തുറക്കുക", marketplaceProfile: "പ്രൊഫൈൽ", marketplaceRequest: "അഭ്യർത്ഥിക്കുക", bookingLoading: "സുരക്ഷിത ബുക്കിംഗുകൾ ലോഡ് ചെയ്യുന്നു…", bookingNone: "ഡെമോ ബുക്കിംഗുകളില്ല", bookingBrowse: "ഡെമോ പ്രൊഫൈലുകൾ കാണുക", bookingView: "വിവരങ്ങൾ കാണുക",
    navReporter: "റിപ്പോർട്ടറുടെ വിവരങ്ങൾ", navReview: "റിപ്പോർട്ട് പരിശോധിക്കുക", navConfirmation: "സമർപ്പണ സ്ഥിരീകരണം", navTrack: "റിപ്പോർട്ട് കണ്ടെത്തുക", navMyReports: "എന്റെ റിപ്പോർട്ടുകൾ",
    navIncident: "സംഭവത്തിന്റെ വിവരങ്ങൾ", navTimeline: "സ്ഥിതി സമയരേഖ", navSafety: "സുരക്ഷ", navEmergency: "അടിയന്തരാവസ്ഥ", reportAction: "പാമ്പിനെ കണ്ടത് റിപ്പോർട്ട് ചെയ്യുക",
    reportsAction: "എന്റെ റിപ്പോർട്ടുകൾ കാണുക", safetyAction: "പാമ്പ് സുരക്ഷ", emergencyAction: "അടിയന്തര വിവരം", language: "ഭാഷ", description: "കണ്ടതിന്റെ വിവരണം",
    sightingTime: "കണ്ട തീയതിയും സമയവും", triageTitle: "സുരക്ഷാ വിലയിരുത്തൽ", bittenQuestion: "ആർക്കെങ്കിലും കടിയേറ്റോ പരിക്കേറ്റോ?", visibleQuestion: "പാമ്പ് ഇപ്പോൾ കാണുന്നുണ്ടോ?",
    dangerQuestion: "ആരെങ്കിലും ഉടനടി അപകടത്തിലാണോ?", yes: "അതെ", no: "അല്ല", call112: "112-ലേക്ക് വിളിക്കുക", chooseState: "സംസ്ഥാനം തിരഞ്ഞെടുക്കുക", chooseDistrict: "ജില്ല തിരഞ്ഞെടുക്കുക",
    city: "നഗരം അല്ലെങ്കിൽ ഗ്രാമം", useLocation: "എന്റെ നിലവിലെ സ്ഥലം ഉപയോഗിക്കുക", refreshLocation: "സ്ഥലം പുതുക്കുക", photoSafety: "ചിത്രത്തിനായി പാമ്പിനടുത്തേക്ക് പോകരുത്. ചിത്രങ്ങൾ ആവശ്യമില്ല.",
    choosePhotos: "ചിത്രങ്ങൾ തിരഞ്ഞെടുക്കുക", remove: "നീക്കം ചെയ്യുക", reporterName: "പേര്", contactPhone: "ബന്ധപ്പെടാനുള്ള നമ്പർ", reporterEmail: "ഇമെയിൽ (ഐച്ഛികം)", submit: "ഡെമോ സംഭവം സമർപ്പിക്കുക",
    confirmationTitle: "ഡെമോ റിപ്പോർട്ട് സംരക്ഷിച്ചു", reference: "റഫറൻസ്", myReportsTitle: "എന്റെ റിപ്പോർട്ടുകൾ", noReports: "ഡെമോ റിപ്പോർട്ടുകളില്ല.", retry: "വീണ്ടും ശ്രമിക്കുക",
    statusCREATED: "സൃഷ്ടിച്ചു", statusUNDER_REVIEW: "പരിശോധനയിലാണ്", statusASSIGNED: "നിയോഗിച്ചു (സിമുലേറ്റഡ്)", statusIN_PROGRESS: "പുരോഗതിയിലാണ് (സിമുലേറ്റഡ്)",
    statusRESOLVED: "പരിഹരിച്ചു", statusCLOSED: "അടച്ചു", statusCANCELLED: "റദ്ദാക്കി", statusUNABLE_TO_ASSIST: "സഹായിക്കാൻ കഴിഞ്ഞില്ല",
    safetyTitle: "പാമ്പ് സുരക്ഷ", safetyDistance: "സുരക്ഷിത അകലം പാലിച്ച് പാമ്പിന് പോകാൻ വഴിയൊരുക്കുക.", safetyDoNotTouch: "പാമ്പിനെ തൊടുകയോ പിടിക്കുകയോ പ്രകോപിപ്പിക്കുകയോ ചെയ്യരുത്.",
    safetyChildren: "കുട്ടികളെയും വളർത്തുമൃഗങ്ങളെയും അകറ്റി നിർത്തുക.", safetyNoRescue: "സ്വയം രക്ഷാപ്രവർത്തനം നടത്തരുത്.", safetyMedical: "പാമ്പുകടി സംശയമുണ്ടെങ്കിൽ ഉടൻ വൈദ്യസഹായം തേടി 112-ലേക്ക് വിളിക്കുക.",
  },
};
const warnedMissingKeys = new Set<string>();

export const CRITICAL_TRANSLATIONS_HUMAN_REVIEWED: Record<Locale, boolean> = {
  en: true,
  te: false,
  ta: false,
  kn: false,
  ml: false,
};

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => Promise<void>;
  t: (key: TranslationKey) => string;
  criticalTranslationsReviewed: boolean;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function LanguageProvider({children}: {children: ReactNode}) {
  const [locale, setLocaleState] = useState<Locale>("en");
  useEffect(() => {
    SecureStore.getItemAsync("spilton_locale").then(value => {
      if (LANGUAGES.some(language => language.code === value)) setLocaleState(value as Locale);
    }).catch(() => undefined);
  }, []);
  const value = useMemo<I18nContextValue>(() => ({
    locale,
    setLocale: async next => {
      setLocaleState(next);
      await SecureStore.setItemAsync("spilton_locale", next);
    },
    t: key => {
      const warningKey = `${locale}:${key}`;
      if (__DEV__ && locale !== "en" && !translations[locale][key] && !warnedMissingKeys.has(warningKey)) {
        warnedMissingKeys.add(warningKey);
        console.warn(`[i18n] Missing ${locale} translation for ${key}; using English fallback.`);
      }
      return translations[locale][key] ?? ENGLISH[key];
    },
    criticalTranslationsReviewed: CRITICAL_TRANSLATIONS_HUMAN_REVIEWED[locale],
  }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside LanguageProvider");
  return context;
}
