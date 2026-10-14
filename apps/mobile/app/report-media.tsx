import {useState} from "react";
import {Image, StyleSheet, View} from "react-native";
import * as ImagePicker from "expo-image-picker";
import {useRouter} from "expo-router";
import {Button, HelperText, Text} from "react-native-paper";
import {InfoCard} from "@/components/cards";
import {Screen} from "@/components/screen";
import {useReportDraft} from "@/features/report/report-context";
import type {SelectedMedia} from "@/features/report/types";
import {useI18n} from "@/services/i18n";

const MAX_FILES = 3;
const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function inferMimeType(asset: ImagePicker.ImagePickerAsset) {
  const provided = asset.mimeType?.toLowerCase();
  if (provided === "image/jpg") return "image/jpeg";
  if (provided && ALLOWED_TYPES.has(provided)) return provided;
  const name = (asset.fileName ?? asset.uri).toLowerCase().split("?")[0];
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
  if (name.endsWith(".png")) return "image/png";
  if (name.endsWith(".webp")) return "image/webp";
  return undefined;
}

async function checkedAsset(asset: ImagePicker.ImagePickerAsset): Promise<SelectedMedia | null> {
  const mimeType = inferMimeType(asset);
  if (!mimeType) return null;
  let fileSize = asset.fileSize;
  if (fileSize == null) {
    try {
      fileSize = (await (await fetch(asset.uri)).blob()).size;
    } catch {
      return null;
    }
  }
  if (fileSize <= 0 || fileSize > MAX_FILE_SIZE) return null;
  const extension = mimeType === "image/jpeg" ? "jpg" : mimeType.split("/")[1];
  return {
    uri: asset.uri,
    fileName: asset.fileName ?? `sighting-${Date.now()}.${extension}`,
    mimeType: mimeType as SelectedMedia["mimeType"],
    fileSize,
  };
}

export default function ReportMedia() {
  const router = useRouter();
  const {draft, update} = useReportDraft();
  const {t} = useI18n();
  const [error, setError] = useState("");
  const [picking, setPicking] = useState(false);

  async function pickImages() {
    setError("");
    const remaining = MAX_FILES - draft.media.length;
    if (remaining <= 0) return;
    setPicking(true);
    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        setError(t("photoPermissionDenied"));
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsMultipleSelection: true,
        selectionLimit: remaining,
        quality: 1,
      });
      if (result.canceled) return;
      const checked = await Promise.all(result.assets.slice(0, remaining).map(checkedAsset));
      const accepted = checked.filter((asset): asset is SelectedMedia => asset != null);
      const deduplicated = accepted.filter(asset => !draft.media.some(current => current.uri === asset.uri));
      update("media", [...draft.media, ...deduplicated].slice(0, MAX_FILES));
      if (accepted.length !== result.assets.slice(0, remaining).length) setError(t("photoInvalid"));
    } catch {
      setError(t("photoInvalid"));
    } finally {
      setPicking(false);
    }
  }

  return (
    <Screen title={t("photosTitle")} subtitle={t("photosSubtitle")}>
      <InfoCard title="Safety first">{t("photoSafety")}</InfoCard>
      {draft.media.map((media, index) => (
        <View key={media.uri} style={styles.previewCard}>
          <Image source={{uri:media.uri}} style={styles.preview} accessibilityLabel={`Selected photo ${index + 1}`} />
          <View style={styles.previewDetails}>
            <Text numberOfLines={2} style={styles.fileName}>{media.fileName}</Text>
            <Text variant="bodySmall">{(media.fileSize / 1024 / 1024).toFixed(2)} MB</Text>
            <Button icon="delete-outline" textColor="#DC2626" onPress={() => update("media", draft.media.filter(item => item.uri !== media.uri))}>{t("remove")}</Button>
          </View>
        </View>
      ))}
      <HelperText type="error" visible={Boolean(error)}>{error}</HelperText>
      {draft.media.length < MAX_FILES && (
        <Button mode="outlined" icon="image-plus" loading={picking} disabled={picking} onPress={() => void pickImages()}>
          {draft.media.length ? t("addMorePhotos") : t("choosePhotos")}
        </Button>
      )}
      <Text variant="bodySmall">{draft.media.length} / {MAX_FILES} photos selected</Text>
      <Button mode="contained" contentStyle={styles.touchTarget} onPress={() => router.push("/report-reporter")}>{t("continueReporter")}</Button>
    </Screen>
  );
}

const styles = StyleSheet.create({
  previewCard: {backgroundColor:"white", borderColor:"#e2e8f0", borderRadius:14, borderWidth:1, flexDirection:"row", overflow:"hidden"},
  preview: {height:132, width:132, backgroundColor:"#e2e8f0"},
  previewDetails: {flex:1, justifyContent:"center", padding:12},
  fileName: {fontWeight:"700"},
  touchTarget: {minHeight:48},
});

