import {MD3LightTheme} from "react-native-paper";
export const colors={forest:"#14532D",emerald:"#16A34A",white:"#FFFFFF",mist:"#F8FAFC",ink:"#111827",danger:"#DC2626"};
export const theme={...MD3LightTheme,colors:{...MD3LightTheme.colors,primary:colors.forest,secondary:colors.emerald,error:colors.danger,background:colors.mist,surface:colors.white}};

