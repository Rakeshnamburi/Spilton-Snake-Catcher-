import {useCallback, useEffect, useState} from "react";
import {Alert, StyleSheet, View} from "react-native";
import {Button, Card, Text, TextInput} from "react-native-paper";
import {api} from "@/services/api";
import {colors} from "@/services/theme";

type Message = {id: string; sender_role: string; body: string; created_at: string};
type Contact = {
  proxy_number: string;
  label: string;
  connectable: boolean;
  message: string;
  counterpart_role: string;
  real_number_hidden: boolean;
};

/** In-app chat between the customer and the assigned demo rescuer. */
export function BookingChatPanel({bookingId}: {bookingId: string}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setMessages(await api<Message[]>(`/api/v1/bookings/${encodeURIComponent(bookingId)}/messages`));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Chat unavailable.");
    }
  }, [bookingId]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 8000);
    return () => clearInterval(timer);
  }, [load]);

  async function send() {
    if (!draft.trim() || busy) return;
    setBusy(true);
    try {
      await api(`/api/v1/bookings/${encodeURIComponent(bookingId)}/messages`, {
        method: "POST",
        body: JSON.stringify({body: draft.trim()}),
      });
      setDraft("");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Message could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return <Card><Card.Content style={styles.stack}>
    <Text variant="titleLarge" style={styles.title}>Message in the app</Text>
    <Text style={styles.caption}>Phone numbers stay hidden. Tell the rescuer exactly where the snake is, or how to find your gate.</Text>
    {messages.length === 0
      ? <Text style={styles.caption}>No messages yet.</Text>
      : messages.map((message) => <View key={message.id} style={[styles.bubble, message.sender_role === "CUSTOMER" ? styles.bubbleMine : styles.bubbleTheirs]}>
          <Text style={[styles.bubbleMeta, message.sender_role === "CUSTOMER" ? styles.metaMine : null]}>{message.sender_role === "CUSTOMER" ? "You" : "Demo rescuer"} · {new Date(message.created_at).toLocaleTimeString()}</Text>
          <Text style={message.sender_role === "CUSTOMER" ? styles.bubbleTextMine : styles.bubbleText}>{message.body}</Text>
        </View>)}
    <TextInput mode="outlined" label="Type a message" value={draft} onChangeText={setDraft} maxLength={1000}/>
    <Button mode="contained" icon="send" loading={busy} disabled={busy} onPress={() => void send()}>Send</Button>
    {error ? <Text style={styles.error}>{error}</Text> : null}
  </Card.Content></Card>;
}

/**
 * Masked calling line, like a delivery app's proxy number. The counterpart's
 * real phone number never reaches the device — only this platform proxy.
 */
export function MaskedCallPanel({bookingId}: {bookingId: string}) {
  const [contact, setContact] = useState<Contact | null>(null);

  const load = useCallback(async () => {
    try {
      setContact(await api<Contact>(`/api/v1/bookings/${encodeURIComponent(bookingId)}/contact`));
    } catch {
      setContact(null);
    }
  }, [bookingId]);

  useEffect(() => { void load(); }, [load]);

  if (!contact) return null;
  const who = contact.counterpart_role === "CUSTOMER" ? "the customer" : "your rescuer";

  return <Card><Card.Content style={styles.stack}>
    <Text variant="titleLarge" style={styles.title}>Masked calling line</Text>
    <Text style={styles.caption}>Call {who} without sharing either real phone number — calls route through a platform proxy number.</Text>
    <View style={styles.proxyBox}>
      <Text style={styles.proxyLabel}>{contact.label}</Text>
      <Text style={styles.proxyNumber}>{contact.proxy_number}</Text>
      <Text style={styles.proxyHint}>Real number hidden from both sides</Text>
    </View>
    <Text style={contact.connectable ? styles.active : styles.caption}>{contact.message}</Text>
    <Button
      mode="contained"
      icon="phone"
      disabled={!contact.connectable}
      onPress={() => Alert.alert("Demo only", `In production this connects the call through ${contact.proxy_number}. No real call is placed.`)}
    >
      {contact.connectable ? "Call via masked line" : "Masked line not active yet"}
    </Button>
  </Card.Content></Card>;
}

const styles = StyleSheet.create({
  stack: {gap: 10},
  title: {fontWeight: "900", color: colors.forest},
  caption: {fontSize: 12, color: "#64748B", lineHeight: 18},
  bubble: {borderRadius: 14, padding: 10, maxWidth: "88%"},
  bubbleMine: {alignSelf: "flex-end", backgroundColor: colors.forest},
  bubbleTheirs: {alignSelf: "flex-start", backgroundColor: "#F1F5F9"},
  bubbleMeta: {fontSize: 10, fontWeight: "800", color: "#64748B", textTransform: "uppercase"},
  metaMine: {color: "#BBF7D0"},
  bubbleText: {color: "#0F172A", lineHeight: 20},
  bubbleTextMine: {color: "white", lineHeight: 20},
  proxyBox: {backgroundColor: "#F1F5F9", borderRadius: 14, padding: 16, gap: 4},
  proxyLabel: {fontSize: 11, fontWeight: "800", color: "#64748B", textTransform: "uppercase"},
  proxyNumber: {fontSize: 26, fontWeight: "900", color: colors.forest, letterSpacing: 1},
  proxyHint: {fontSize: 11, fontWeight: "800", color: colors.emerald},
  active: {fontSize: 13, fontWeight: "800", color: colors.forest, lineHeight: 19},
  error: {color: colors.danger, fontWeight: "700"},
});
