import {useState} from "react";
import {Button, Menu} from "react-native-paper";
import {LANGUAGES, useI18n} from "@/services/i18n";

export function LanguageSelector() {
  const [open, setOpen] = useState(false);
  const {locale, setLocale, t} = useI18n();
  const selected = LANGUAGES.find(language => language.code === locale) ?? LANGUAGES[0];
  return (
    <Menu
      visible={open}
      onDismiss={() => setOpen(false)}
      anchor={<Button mode="outlined" icon="translate" onPress={() => setOpen(true)}>{t("language")}: {selected.label}</Button>}
    >
      {LANGUAGES.map(language => (
        <Menu.Item
          key={language.code}
          title={language.label}
          leadingIcon={language.code === locale ? "check" : undefined}
          onPress={() => { void setLocale(language.code).catch(() => undefined); setOpen(false); }}
        />
      ))}
    </Menu>
  );
}
