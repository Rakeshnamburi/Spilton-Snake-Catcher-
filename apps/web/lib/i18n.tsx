"use client";

import {createContext, useCallback, useContext, useEffect, useMemo, useState} from "react";

export const LANGUAGES = ["en", "te", "ta", "kn", "ml"] as const;
export type Language = typeof LANGUAGES[number];
type Dictionary = Record<string, string>;

const en: Dictionary = {
  "nav.report": "Report", "nav.track": "Track", "nav.myReports": "My reports", "nav.safety": "Safety",
  "nav.emergency": "Emergency", "nav.about": "About", "nav.contact": "Contact", "nav.signIn": "Sign in",
  "nav.rescuers": "Demo rescuers", "nav.bookings": "Bookings", "nav.rescuerDesk": "Rescuer desk",
  "nav.language": "Language", "demo.banner": "DEMO PLATFORM — Not an active emergency rescue service. For a medical emergency, call 112.",
  "report.title": "Report a snake sighting", "report.demo": "This creates a private demo record. No rescuer will be dispatched.",
  "report.stayBack": "Stay back. Never approach, touch, trap, or provoke a snake, including to take a photo.",
  "report.step.incident": "Incident", "report.step.triage": "Safety triage", "report.step.location": "Location",
  "report.step.media": "Optional media", "report.step.reporter": "Reporter", "report.step.review": "Review",
  "report.state": "State", "report.district": "District", "report.city": "City or village", "report.landmark": "Landmark (optional)",
  "report.address": "Address description (optional)", "report.sightedAt": "Date and time of sighting", "report.description": "What did you observe?",
  "report.injury": "Is anyone bitten or injured?", "report.visible": "Is the snake currently visible?",
  "report.danger": "Is anyone in immediate danger?", "common.yes": "Yes", "common.no": "No",
  "report.medical": "Call 112 and seek immediate medical care now. Submitting this report is not a substitute for emergency help.",
  "report.gps": "Use my current location", "report.refreshGps": "Refresh location", "report.latitude": "Latitude",
  "report.longitude": "Longitude", "report.accuracy": "Accuracy", "report.confirmLocation": "I have reviewed this location.",
  "report.locationManual": "GPS is optional. State, district, city and manual coordinates remain available.",
  "report.photos": "Add up to 3 photos (optional)", "report.photoSafety": "Only use a photo already taken from a safe distance. Do not move closer.",
  "report.name": "Reporter name", "report.phone": "Contact number", "report.email": "Email (optional)",
  "report.consent": "I understand this is a demo record and consent to storing these details.",
  "report.previous": "Previous", "report.next": "Continue", "report.submit": "Submit demo report", "report.submitting": "Submitting safely…",
  "report.success": "Demo report submitted", "report.confirmation": "No real rescue team has been notified or dispatched.",
  "report.edit": "Edit", "report.remove": "Remove", "report.locationCaptured": "Location captured. Review the marker or coordinates before continuing.",
  "report.gpsLoading": "Requesting location permission…", "report.gpsDenied": "Location permission was denied. Manual location works normally.",
  "report.gpsTimeout": "Location request timed out. Retry or enter the location manually.", "report.gpsUnavailable": "Location is unavailable on this device. Use manual entry.",
  "safety.title": "Snake safety", "safety.distance": "Keep a safe distance and give the snake a clear escape route.",
  "safety.noTouch": "Do not touch, trap, corner, provoke, or attempt to capture the snake.", "safety.people": "Move children and pets well away.",
  "safety.noRescue": "Do not attempt a rescue yourself; contact authorized local wildlife assistance.",
  "safety.photo": "A photo is optional—never move closer to take one.", "safety.bite": "For suspected snakebite, seek immediate medical care and call 112.",
  "status.CREATED": "Created", "status.UNDER_REVIEW": "Under review", "status.ASSIGNED": "Assigned (demo)",
  "status.IN_PROGRESS": "In progress (demo)", "status.RESOLVED": "Resolved", "status.CLOSED": "Closed",
  "status.CANCELLED": "Cancelled", "status.UNABLE_TO_ASSIST": "Unable to assist",
  "error.required": "This field is required.", "error.network": "The service could not be reached. Check your connection and try again.",
  "error.session": "Your session has expired. Sign in and try again.", "error.duplicate": "This report was already submitted.",
  "review.required": "Critical safety translation requires human review before operational use.",
};

const te: Dictionary = {
  "nav.report":"నివేదించండి","nav.track":"ట్రాక్ చేయండి","nav.myReports":"నా నివేదికలు","nav.safety":"భద్రత","nav.emergency":"అత్యవసరం","nav.about":"గురించి","nav.contact":"సంప్రదించండి","nav.signIn":"సైన్ ఇన్","nav.language":"భాష",
  "demo.banner":"డెమో ప్లాట్‌ఫారమ్ — ఇది క్రియాశీల అత్యవసర రక్షణ సేవ కాదు. వైద్య అత్యవసర పరిస్థితిలో 112కి కాల్ చేయండి.","report.title":"పాము కనిపించిన విషయాన్ని నివేదించండి","report.demo":"ఇది ప్రైవేట్ డెమో రికార్డును సృష్టిస్తుంది. రక్షకుడు పంపబడరు.","report.stayBack":"దూరంగా ఉండండి. ఫోటో కోసం కూడా పామును చేరుకోవద్దు, తాకవద్దు, పట్టుకోవద్దు లేదా రెచ్చగొట్టవద్దు.",
  "report.step.incident":"సంఘటన","report.step.triage":"భద్రతా అంచనా","report.step.location":"ప్రదేశం","report.step.media":"ఐచ్ఛిక మీడియా","report.step.reporter":"నివేదించే వ్యక్తి","report.step.review":"సమీక్ష",
  "report.state":"రాష్ట్రం","report.district":"జిల్లా","report.city":"నగరం లేదా గ్రామం","report.landmark":"గుర్తింపు స్థలం (ఐచ్ఛికం)","report.address":"చిరునామా వివరణ (ఐచ్ఛికం)","report.sightedAt":"చూసిన తేదీ మరియు సమయం","report.description":"మీరు ఏమి గమనించారు?","report.injury":"ఎవరైనా కాటుకు గురయ్యారా లేదా గాయపడ్డారా?","report.visible":"పాము ప్రస్తుతం కనిపిస్తోందా?","report.danger":"ఎవరైనా తక్షణ ప్రమాదంలో ఉన్నారా?","common.yes":"అవును","common.no":"కాదు",
  "report.medical":"ఇప్పుడే 112కి కాల్ చేసి తక్షణ వైద్య సహాయం పొందండి. ఈ నివేదిక అత్యవసర వైద్య సహాయానికి ప్రత్యామ్నాయం కాదు.","report.gps":"నా ప్రస్తుత స్థానాన్ని ఉపయోగించండి","report.refreshGps":"స్థానాన్ని రిఫ్రెష్ చేయండి","report.latitude":"అక్షాంశం","report.longitude":"రేఖాంశం","report.accuracy":"ఖచ్చితత్వం","report.confirmLocation":"నేను ఈ స్థానాన్ని సమీక్షించాను.","report.locationManual":"GPS ఐచ్ఛికం. మాన్యువల్ స్థానం ఎల్లప్పుడూ అందుబాటులో ఉంటుంది.","report.photos":"3 ఫోటోల వరకు జోడించండి (ఐచ్ఛికం)","report.photoSafety":"సురక్షిత దూరం నుండి ఇప్పటికే తీసిన ఫోటోను మాత్రమే ఉపయోగించండి. దగ్గరకు వెళ్లవద్దు.","report.name":"నివేదించే వ్యక్తి పేరు","report.phone":"సంప్రదింపు నంబర్","report.email":"ఇమెయిల్ (ఐచ్ఛికం)","report.consent":"ఇది డెమో రికార్డు అని అర్థం చేసుకుని వివరాలను నిల్వ చేయడానికి సమ్మతిస్తున్నాను.","report.previous":"వెనుకకు","report.next":"కొనసాగించండి","report.submit":"డెమో నివేదిక పంపండి","report.submitting":"సురక్షితంగా పంపుతోంది…","report.success":"డెమో నివేదిక పంపబడింది","report.confirmation":"నిజమైన రక్షణ బృందానికి సమాచారం ఇవ్వలేదు లేదా పంపలేదు.","report.edit":"సవరించండి","report.remove":"తొలగించండి","report.locationCaptured":"స్థానం పొందబడింది. కొనసాగించే ముందు సమీక్షించండి.","report.gpsLoading":"స్థాన అనుమతి అడుగుతోంది…","report.gpsDenied":"స్థాన అనుమతి నిరాకరించబడింది. మాన్యువల్ స్థానం పనిచేస్తుంది.","report.gpsTimeout":"స్థాన అభ్యర్థన సమయం ముగిసింది. మళ్లీ ప్రయత్నించండి లేదా మాన్యువల్‌గా నమోదు చేయండి.","report.gpsUnavailable":"ఈ పరికరంలో స్థానం అందుబాటులో లేదు. మాన్యువల్ ఎంట్రీ ఉపయోగించండి.",
  "safety.title":"పాము భద్రత","safety.distance":"సురక్షిత దూరం పాటించి పాముకు వెళ్లే మార్గం ఇవ్వండి.","safety.noTouch":"పామును తాకవద్దు, బంధించవద్దు, మూలకు నెట్టవద్దు, రెచ్చగొట్టవద్దు లేదా పట్టుకోవడానికి ప్రయత్నించవద్దు.","safety.people":"పిల్లలు మరియు పెంపుడు జంతువులను దూరంగా ఉంచండి.","safety.noRescue":"మీరే రక్షించడానికి ప్రయత్నించవద్దు; అధీకృత స్థానిక వన్యప్రాణి సహాయాన్ని సంప్రదించండి.","safety.photo":"ఫోటో ఐచ్ఛికం—తీయడానికి దగ్గరకు వెళ్లవద్దు.","safety.bite":"పాము కాటు అనుమానం ఉంటే తక్షణ వైద్య సహాయం పొందండి మరియు 112కి కాల్ చేయండి.",
};

const ta: Dictionary = {
  "nav.report":"புகாரளிக்கவும்","nav.track":"கண்காணிக்கவும்","nav.myReports":"என் புகார்கள்","nav.safety":"பாதுகாப்பு","nav.emergency":"அவசரம்","nav.about":"பற்றி","nav.contact":"தொடர்பு","nav.signIn":"உள்நுழை","nav.language":"மொழி",
  "demo.banner":"டெமோ தளம் — இது செயலில் உள்ள அவசர மீட்பு சேவை அல்ல. மருத்துவ அவசரத்திற்கு 112-ஐ அழைக்கவும்.","report.title":"பாம்பு கண்டதைப் புகாரளிக்கவும்","report.demo":"இது தனிப்பட்ட டெமோ பதிவை உருவாக்கும். மீட்பாளர் அனுப்பப்படமாட்டார்.","report.stayBack":"விலகி இருங்கள். புகைப்படத்திற்காகவும் பாம்பை நெருங்கவோ, தொடவோ, பிடிக்கவோ, தூண்டவோ வேண்டாம்.",
  "report.step.incident":"சம்பவம்","report.step.triage":"பாதுகாப்பு மதிப்பீடு","report.step.location":"இடம்","report.step.media":"விருப்ப ஊடகம்","report.step.reporter":"புகாரளிப்பவர்","report.step.review":"மதிப்பாய்வு","report.state":"மாநிலம்","report.district":"மாவட்டம்","report.city":"நகரம் அல்லது கிராமம்","report.landmark":"அடையாள இடம் (விருப்பம்)","report.address":"முகவரி விளக்கம் (விருப்பம்)","report.sightedAt":"கண்ட தேதி மற்றும் நேரம்","report.description":"நீங்கள் என்ன கவனித்தீர்கள்?","report.injury":"யாரையாவது பாம்பு கடித்ததா அல்லது காயமடைந்தார்களா?","report.visible":"பாம்பு தற்போது தெரிகிறதா?","report.danger":"யாராவது உடனடி ஆபத்தில் உள்ளார்களா?","common.yes":"ஆம்","common.no":"இல்லை",
  "report.medical":"இப்போதே 112-ஐ அழைத்து உடனடி மருத்துவ உதவி பெறுங்கள். இந்தப் புகார் அவசர மருத்துவ உதவிக்கு மாற்றாகாது.","report.gps":"என் தற்போதைய இடத்தைப் பயன்படுத்து","report.refreshGps":"இடத்தைப் புதுப்பி","report.latitude":"அட்சரேகை","report.longitude":"தீர்க்கரேகை","report.accuracy":"துல்லியம்","report.confirmLocation":"இந்த இடத்தை நான் சரிபார்த்தேன்.","report.locationManual":"GPS விருப்பமானது. கைமுறை இடம் எப்போதும் கிடைக்கும்.","report.photos":"3 புகைப்படங்கள் வரை சேர்க்கவும் (விருப்பம்)","report.photoSafety":"பாதுகாப்பான தூரத்திலிருந்து ஏற்கனவே எடுத்த படத்தை மட்டும் பயன்படுத்தவும். நெருங்க வேண்டாம்.","report.name":"புகாரளிப்பவர் பெயர்","report.phone":"தொடர்பு எண்","report.email":"மின்னஞ்சல் (விருப்பம்)","report.consent":"இது டெமோ பதிவு என்பதை புரிந்து விவரங்களை சேமிக்க ஒப்புக்கொள்கிறேன்.","report.previous":"முந்தையது","report.next":"தொடரவும்","report.submit":"டெமோ புகாரைச் சமர்ப்பிக்கவும்","report.submitting":"பாதுகாப்பாக சமர்ப்பிக்கிறது…","report.success":"டெமோ புகார் சமர்ப்பிக்கப்பட்டது","report.confirmation":"உண்மையான மீட்புக் குழுவுக்கு தகவல் அளிக்கவோ அனுப்பவோ இல்லை.","report.edit":"திருத்து","report.remove":"நீக்கு","report.locationCaptured":"இடம் பெறப்பட்டது. தொடரும் முன் சரிபார்க்கவும்.","report.gpsLoading":"இட அனுமதி கோரப்படுகிறது…","report.gpsDenied":"இட அனுமதி மறுக்கப்பட்டது. கைமுறை இடம் இயங்கும்.","report.gpsTimeout":"இடக் கோரிக்கை காலாவதியானது. மீண்டும் முயலவும் அல்லது கைமுறையாக உள்ளிடவும்.","report.gpsUnavailable":"இந்தச் சாதனத்தில் இடம் கிடைக்கவில்லை. கைமுறையாக உள்ளிடவும்.",
  "safety.title":"பாம்பு பாதுகாப்பு","safety.distance":"பாதுகாப்பான தூரத்தைப் பேணி பாம்பு வெளியேற வழிவிடுங்கள்.","safety.noTouch":"பாம்பை தொடவோ, அடைக்கவோ, மூலையில் தள்ளவோ, தூண்டவோ, பிடிக்கவோ முயலாதீர்கள்.","safety.people":"குழந்தைகள் மற்றும் செல்லப்பிராணிகளைத் தொலைவில் வைக்கவும்.","safety.noRescue":"நீங்களே மீட்க முயலாதீர்கள்; அங்கீகரிக்கப்பட்ட உள்ளூர் வனவிலங்கு உதவியைத் தொடர்புகொள்ளுங்கள்.","safety.photo":"புகைப்படம் விருப்பமானது—எடுக்க நெருங்காதீர்கள்.","safety.bite":"பாம்புக்கடி சந்தேகம் இருந்தால் உடனடி மருத்துவ உதவி பெற்று 112-ஐ அழைக்கவும்.",
};

const kn: Dictionary = {
  "nav.report":"ವರದಿ ಮಾಡಿ","nav.track":"ಟ್ರ್ಯಾಕ್ ಮಾಡಿ","nav.myReports":"ನನ್ನ ವರದಿಗಳು","nav.safety":"ಸುರಕ್ಷತೆ","nav.emergency":"ತುರ್ತು","nav.about":"ಕುರಿತು","nav.contact":"ಸಂಪರ್ಕ","nav.signIn":"ಸೈನ್ ಇನ್","nav.language":"ಭಾಷೆ",
  "demo.banner":"ಡೆಮೊ ವೇದಿಕೆ — ಇದು ಸಕ್ರಿಯ ತುರ್ತು ರಕ್ಷಣಾ ಸೇವೆಯಲ್ಲ. ವೈದ್ಯಕೀಯ ತುರ್ತು ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ 112ಕ್ಕೆ ಕರೆ ಮಾಡಿ.","report.title":"ಹಾವು ಕಂಡ ಬಗ್ಗೆ ವರದಿ ಮಾಡಿ","report.demo":"ಇದು ಖಾಸಗಿ ಡೆಮೊ ದಾಖಲೆಯನ್ನು ಸೃಷ್ಟಿಸುತ್ತದೆ. ರಕ್ಷಕರನ್ನು ಕಳುಹಿಸಲಾಗುವುದಿಲ್ಲ.","report.stayBack":"ದೂರವಿರಿ. ಫೋಟೋ ತೆಗೆಯಲು ಸಹ ಹಾವಿನ ಹತ್ತಿರ ಹೋಗಬೇಡಿ, ಮುಟ್ಟಬೇಡಿ, ಹಿಡಿಯಬೇಡಿ ಅಥವಾ ಕೆರಳಿಸಬೇಡಿ.",
  "report.step.incident":"ಘಟನೆ","report.step.triage":"ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ","report.step.location":"ಸ್ಥಳ","report.step.media":"ಐಚ್ಛಿಕ ಮಾಧ್ಯಮ","report.step.reporter":"ವರದಿದಾರ","report.step.review":"ಪರಿಶೀಲನೆ","report.state":"ರಾಜ್ಯ","report.district":"ಜಿಲ್ಲೆ","report.city":"ನಗರ ಅಥವಾ ಗ್ರಾಮ","report.landmark":"ಗುರುತು ಸ್ಥಳ (ಐಚ್ಛಿಕ)","report.address":"ವಿಳಾಸ ವಿವರಣೆ (ಐಚ್ಛಿಕ)","report.sightedAt":"ಕಂಡ ದಿನಾಂಕ ಮತ್ತು ಸಮಯ","report.description":"ನೀವು ಏನು ಗಮನಿಸಿದ್ದೀರಿ?","report.injury":"ಯಾರಿಗಾದರೂ ಕಚ್ಚಿದೆಯೇ ಅಥವಾ ಗಾಯವಾಗಿದೆಯೇ?","report.visible":"ಹಾವು ಈಗ ಕಾಣುತ್ತಿದೆಯೇ?","report.danger":"ಯಾರಾದರೂ ತಕ್ಷಣದ ಅಪಾಯದಲ್ಲಿದ್ದಾರೆಯೇ?","common.yes":"ಹೌದು","common.no":"ಇಲ್ಲ",
  "report.medical":"ಈಗಲೇ 112ಕ್ಕೆ ಕರೆ ಮಾಡಿ ತಕ್ಷಣ ವೈದ್ಯಕೀಯ ನೆರವು ಪಡೆಯಿರಿ. ಈ ವರದಿ ತುರ್ತು ವೈದ್ಯಕೀಯ ನೆರವಿಗೆ ಪರ್ಯಾಯವಲ್ಲ.","report.gps":"ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳ ಬಳಸಿ","report.refreshGps":"ಸ್ಥಳ ರಿಫ್ರೆಶ್ ಮಾಡಿ","report.latitude":"ಅಕ್ಷಾಂಶ","report.longitude":"ರೇಖಾಂಶ","report.accuracy":"ನಿಖರತೆ","report.confirmLocation":"ಈ ಸ್ಥಳವನ್ನು ನಾನು ಪರಿಶೀಲಿಸಿದ್ದೇನೆ.","report.locationManual":"GPS ಐಚ್ಛಿಕ. ಕೈಯಾರೆ ಸ್ಥಳ ನಮೂದಿಸುವುದು ಸದಾ ಲಭ್ಯ.","report.photos":"3 ಫೋಟೋಗಳವರೆಗೆ ಸೇರಿಸಿ (ಐಚ್ಛಿಕ)","report.photoSafety":"ಸುರಕ್ಷಿತ ದೂರದಿಂದ ಈಗಾಗಲೇ ತೆಗೆದ ಚಿತ್ರವನ್ನು ಮಾತ್ರ ಬಳಸಿ. ಹತ್ತಿರ ಹೋಗಬೇಡಿ.","report.name":"ವರದಿದಾರರ ಹೆಸರು","report.phone":"ಸಂಪರ್ಕ ಸಂಖ್ಯೆ","report.email":"ಇಮೇಲ್ (ಐಚ್ಛಿಕ)","report.consent":"ಇದು ಡೆಮೊ ದಾಖಲೆ ಎಂದು ಅರ್ಥಮಾಡಿಕೊಂಡು ವಿವರಗಳನ್ನು ಸಂಗ್ರಹಿಸಲು ಒಪ್ಪುತ್ತೇನೆ.","report.previous":"ಹಿಂದೆ","report.next":"ಮುಂದುವರಿಸಿ","report.submit":"ಡೆಮೊ ವರದಿ ಸಲ್ಲಿಸಿ","report.submitting":"ಸುರಕ್ಷಿತವಾಗಿ ಸಲ್ಲಿಸಲಾಗುತ್ತಿದೆ…","report.success":"ಡೆಮೊ ವರದಿ ಸಲ್ಲಿಸಲಾಗಿದೆ","report.confirmation":"ನಿಜವಾದ ರಕ್ಷಣಾ ತಂಡಕ್ಕೆ ಮಾಹಿತಿ ನೀಡಿಲ್ಲ ಅಥವಾ ಕಳುಹಿಸಿಲ್ಲ.","report.edit":"ತಿದ್ದು","report.remove":"ತೆಗೆದುಹಾಕಿ","report.locationCaptured":"ಸ್ಥಳ ಸೆರೆಹಿಡಿಯಲಾಗಿದೆ. ಮುಂದುವರೆಯುವ ಮೊದಲು ಪರಿಶೀಲಿಸಿ.","report.gpsLoading":"ಸ್ಥಳ ಅನುಮತಿ ಕೇಳಲಾಗುತ್ತಿದೆ…","report.gpsDenied":"ಸ್ಥಳ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ಕೈಯಾರೆ ಸ್ಥಳ ಬಳಸಬಹುದು.","report.gpsTimeout":"ಸ್ಥಳ ವಿನಂತಿ ಸಮಯ ಮೀರಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಕೈಯಾರೆ ನಮೂದಿಸಿ.","report.gpsUnavailable":"ಈ ಸಾಧನದಲ್ಲಿ ಸ್ಥಳ ಲಭ್ಯವಿಲ್ಲ. ಕೈಯಾರೆ ನಮೂದಿಸಿ.",
  "safety.title":"ಹಾವು ಸುರಕ್ಷತೆ","safety.distance":"ಸುರಕ್ಷಿತ ದೂರವಿದ್ದು ಹಾವು ಹೊರಹೋಗಲು ದಾರಿ ಬಿಡಿ.","safety.noTouch":"ಹಾವನ್ನು ಮುಟ್ಟಬೇಡಿ, ಸಿಕ್ಕಿಹಾಕಬೇಡಿ, ಮೂಲೆಗುಂಪು ಮಾಡಬೇಡಿ, ಕೆರಳಿಸಬೇಡಿ ಅಥವಾ ಹಿಡಿಯಲು ಪ್ರಯತ್ನಿಸಬೇಡಿ.","safety.people":"ಮಕ್ಕಳು ಮತ್ತು ಸಾಕುಪ್ರಾಣಿಗಳನ್ನು ದೂರವಿಡಿ.","safety.noRescue":"ನೀವೇ ರಕ್ಷಿಸಲು ಪ್ರಯತ್ನಿಸಬೇಡಿ; ಅಧಿಕೃತ ಸ್ಥಳೀಯ ವನ್ಯಜೀವಿ ಸಹಾಯವನ್ನು ಸಂಪರ್ಕಿಸಿ.","safety.photo":"ಫೋಟೋ ಐಚ್ಛಿಕ—ತೆಗೆಯಲು ಹತ್ತಿರ ಹೋಗಬೇಡಿ.","safety.bite":"ಹಾವು ಕಚ್ಚಿದ ಶಂಕೆಯಿದ್ದರೆ ತಕ್ಷಣ ವೈದ್ಯಕೀಯ ನೆರವು ಪಡೆದು 112ಕ್ಕೆ ಕರೆ ಮಾಡಿ.",
};

const ml: Dictionary = {
  "nav.report":"റിപ്പോർട്ട് ചെയ്യുക","nav.track":"ട്രാക്ക് ചെയ്യുക","nav.myReports":"എന്റെ റിപ്പോർട്ടുകൾ","nav.safety":"സുരക്ഷ","nav.emergency":"അടിയന്തര സഹായം","nav.about":"കുറിച്ച്","nav.contact":"ബന്ധപ്പെടുക","nav.signIn":"സൈൻ ഇൻ","nav.language":"ഭാഷ",
  "demo.banner":"ഡെമോ പ്ലാറ്റ്ഫോം — ഇത് സജീവ അടിയന്തര രക്ഷാസേവനമല്ല. മെഡിക്കൽ അടിയന്തരാവസ്ഥയിൽ 112-ലേക്ക് വിളിക്കുക.","report.title":"പാമ്പിനെ കണ്ടത് റിപ്പോർട്ട് ചെയ്യുക","report.demo":"ഇത് സ്വകാര്യ ഡെമോ റെക്കോർഡ് സൃഷ്ടിക്കും. രക്ഷാപ്രവർത്തകനെ അയയ്ക്കില്ല.","report.stayBack":"അകലം പാലിക്കുക. ഫോട്ടോ എടുക്കാൻ പോലും പാമ്പിനടുത്തേക്ക് പോകരുത്, തൊടരുത്, പിടിക്കരുത്, പ്രകോപിപ്പിക്കരുത്.",
  "report.step.incident":"സംഭവം","report.step.triage":"സുരക്ഷാ പരിശോധന","report.step.location":"സ്ഥലം","report.step.media":"ഐച്ഛിക മീഡിയ","report.step.reporter":"റിപ്പോർട്ടർ","report.step.review":"അവലോകനം","report.state":"സംസ്ഥാനം","report.district":"ജില്ല","report.city":"നഗരം അല്ലെങ്കിൽ ഗ്രാമം","report.landmark":"അടയാളസ്ഥലം (ഐച്ഛികം)","report.address":"വിലാസ വിവരണം (ഐച്ഛികം)","report.sightedAt":"കണ്ട തീയതിയും സമയവും","report.description":"നിങ്ങൾ എന്താണ് കണ്ടത്?","report.injury":"ആർക്കെങ്കിലും കടിയോ പരിക്കോ ഏറ്റിട്ടുണ്ടോ?","report.visible":"പാമ്പ് ഇപ്പോഴും കാണുന്നുണ്ടോ?","report.danger":"ആരെങ്കിലും ഉടനടി അപകടത്തിലാണോ?","common.yes":"അതെ","common.no":"അല്ല",
  "report.medical":"ഇപ്പോൾ തന്നെ 112-ലേക്ക് വിളിച്ച് അടിയന്തര വൈദ്യസഹായം തേടുക. ഈ റിപ്പോർട്ട് അടിയന്തര വൈദ്യസഹായത്തിന് പകരമല്ല.","report.gps":"എന്റെ നിലവിലെ സ്ഥലം ഉപയോഗിക്കുക","report.refreshGps":"സ്ഥലം പുതുക്കുക","report.latitude":"അക്ഷാംശം","report.longitude":"രേഖാംശം","report.accuracy":"കൃത്യത","report.confirmLocation":"ഈ സ്ഥലം ഞാൻ പരിശോധിച്ചു.","report.locationManual":"GPS ഐച്ഛികമാണ്. സ്ഥലം കൈകൊണ്ട് നൽകാം.","report.photos":"3 ഫോട്ടോകൾ വരെ ചേർക്കുക (ഐച്ഛികം)","report.photoSafety":"സുരക്ഷിത അകലത്തിൽ നിന്ന് മുമ്പ് എടുത്ത ചിത്രം മാത്രം ഉപയോഗിക്കുക. അടുത്തേക്ക് പോകരുത്.","report.name":"റിപ്പോർട്ടറുടെ പേര്","report.phone":"ബന്ധപ്പെടാനുള്ള നമ്പർ","report.email":"ഇമെയിൽ (ഐച്ഛികം)","report.consent":"ഇത് ഡെമോ റെക്കോർഡ് ആണെന്ന് മനസ്സിലാക്കി വിവരങ്ങൾ സൂക്ഷിക്കാൻ സമ്മതിക്കുന്നു.","report.previous":"പിന്നിലേക്ക്","report.next":"തുടരുക","report.submit":"ഡെമോ റിപ്പോർട്ട് സമർപ്പിക്കുക","report.submitting":"സുരക്ഷിതമായി സമർപ്പിക്കുന്നു…","report.success":"ഡെമോ റിപ്പോർട്ട് സമർപ്പിച്ചു","report.confirmation":"യഥാർത്ഥ രക്ഷാസംഘത്തെ അറിയിക്കുകയോ അയയ്ക്കുകയോ ചെയ്തിട്ടില്ല.","report.edit":"തിരുത്തുക","report.remove":"നീക്കം ചെയ്യുക","report.locationCaptured":"സ്ഥലം ലഭിച്ചു. തുടരുന്നതിന് മുമ്പ് പരിശോധിക്കുക.","report.gpsLoading":"സ്ഥല അനുമതി ചോദിക്കുന്നു…","report.gpsDenied":"സ്ഥല അനുമതി നിരസിച്ചു. കൈകൊണ്ട് സ്ഥലം നൽകാം.","report.gpsTimeout":"സ്ഥല അഭ്യർത്ഥനയുടെ സമയം കഴിഞ്ഞു. വീണ്ടും ശ്രമിക്കുകയോ കൈകൊണ്ട് നൽകുകയോ ചെയ്യുക.","report.gpsUnavailable":"ഈ ഉപകരണത്തിൽ സ്ഥലം ലഭ്യമല്ല. കൈകൊണ്ട് നൽകുക.",
  "safety.title":"പാമ്പ് സുരക്ഷ","safety.distance":"സുരക്ഷിത അകലം പാലിച്ച് പാമ്പിന് രക്ഷപ്പെടാൻ വഴിയൊരുക്കുക.","safety.noTouch":"പാമ്പിനെ തൊടുകയോ കുടുക്കുകയോ വളയുകയോ പ്രകോപിപ്പിക്കുകയോ പിടിക്കാൻ ശ്രമിക്കുകയോ ചെയ്യരുത്.","safety.people":"കുട്ടികളെയും വളർത്തുമൃഗങ്ങളെയും അകറ്റിനിർത്തുക.","safety.noRescue":"സ്വയം രക്ഷിക്കാൻ ശ്രമിക്കരുത്; അംഗീകൃത പ്രാദേശിക വന്യജീവി സഹായവുമായി ബന്ധപ്പെടുക.","safety.photo":"ഫോട്ടോ ഐച്ഛികമാണ്—എടുക്കാൻ അടുത്തേക്ക് പോകരുത്.","safety.bite":"പാമ്പുകടിയെന്ന് സംശയമുണ്ടെങ്കിൽ ഉടൻ വൈദ്യസഹായം തേടി 112-ലേക്ക് വിളിക്കുക.",
};

const dictionaries: Record<Language, Dictionary> = {en, te: {...en, ...te}, ta: {...en, ...ta}, kn: {...en, ...kn}, ml: {...en, ...ml}};
const labels: Record<Language, string> = {en: "English", te: "తెలుగు", ta: "தமிழ்", kn: "ಕನ್ನಡ", ml: "മലയാളം"};

type I18nValue = {language: Language; setLanguage: (language: Language) => void; t: (key: string) => string; languageLabels: typeof labels; needsHumanReview: boolean};
const I18nContext = createContext<I18nValue | null>(null);

export function LanguageProvider({children}: {children: React.ReactNode}) {
  const [language, updateLanguage] = useState<Language>("en");
  useEffect(() => {
    const stored = window.localStorage.getItem("spilton_language");
    if (LANGUAGES.includes(stored as Language)) {
      updateLanguage(stored as Language);
      document.documentElement.lang = stored as Language;
    }
  }, []);
  const setLanguage = useCallback((next: Language) => {
    updateLanguage(next);
    window.localStorage.setItem("spilton_language", next);
    document.documentElement.lang = next;
  }, []);
  const value = useMemo<I18nValue>(() => ({
    language,
    setLanguage,
    t: (key) => dictionaries[language][key] ?? en[key] ?? key,
    languageLabels: labels,
    needsHumanReview: language !== "en",
  }), [language, setLanguage]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside LanguageProvider");
  return value;
}

export function TranslationReviewNotice() {
  const {needsHumanReview, t} = useI18n();
  if (!needsHumanReview) return null;
  return <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">{t("review.required")}</p>;
}
