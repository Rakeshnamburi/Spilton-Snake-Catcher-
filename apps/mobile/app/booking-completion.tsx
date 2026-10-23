import {useFocusEffect, useLocalSearchParams} from "expo-router";
import {useCallback, useState} from "react";
import {StyleSheet, View} from "react-native";
import {Button, Card, SegmentedButtons, Text, TextInput} from "react-native-paper";
import {Screen} from "@/components/screen";
import type {Booking, DemoPayment, RescueEvidence, RescueReport} from "@spilton/shared-types";
import {api, ApiError} from "@/services/api";
import {colors} from "@/services/theme";

export default function BookingCompletionScreen() {
  const {bookingId} = useLocalSearchParams<{bookingId: string}>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [report, setReport] = useState<RescueReport | null>(null);
  const [evidence, setEvidence] = useState<RescueEvidence[]>([]);
  const [payment, setPayment] = useState<DemoPayment | null>(null);
  const [method, setMethod] = useState("NO_CHARGE");
  const [amount, setAmount] = useState("0.00");
  const [rating, setRating] = useState("5");
  const [review, setReview] = useState("");
  const [disputeReason, setDisputeReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!bookingId) return;
    try {
      const current = await api<Booking>("/api/v1/bookings/" + bookingId);
      setBooking(current);
      setReport(await api<RescueReport>("/api/v1/bookings/" + bookingId + "/rescue/report"));
      setEvidence(await api<RescueEvidence[]>("/api/v1/bookings/" + bookingId + "/rescue/evidence"));
      const payments = await api<DemoPayment[]>("/api/v1/payments");
      setPayment(payments.find((item) => item.booking_id === bookingId) ?? null);
      setMessage("");
    } catch (reason) {
      if (!(reason instanceof ApiError && reason.status === 404)) {
        setMessage(reason instanceof Error ? reason.message : "Completion unavailable.");
      }
    }
  }, [bookingId]);
  useFocusEffect(useCallback(() => { void load(); }, [load]));

  async function confirm() {
    if (!bookingId) return;
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + bookingId + "/confirm-completion", {method: "POST"});
      setMessage("Simulated completion confirmed.");
      await load();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Confirmation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function pay() {
    if (!bookingId) return;
    setBusy(true);
    try {
      const created = await api<DemoPayment>("/api/v1/bookings/" + bookingId + "/payments", {
        method: "POST",
        headers: {"Idempotency-Key": "mobile-payment-" + Date.now()},
        body: JSON.stringify({
          method,
          amount: method === "NO_CHARGE" ? "0.00" : amount,
          currency: "INR",
          confirm_demo: true,
        }),
      });
      setPayment(
        created.method === "DEMO_ONLINE"
          ? await api<DemoPayment>("/api/v1/payments/" + created.id + "/confirm", {
            method: "POST",
            body: JSON.stringify({simulate_failure: false}),
          })
          : created,
      );
      setMessage("Demo financial record saved. No real money moved.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Demo payment failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitReview() {
    if (!bookingId) return;
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + bookingId + "/review", {
        method: "POST",
        body: JSON.stringify({rating: Number(rating), review_text: review || null}),
      });
      setMessage("Demo review published.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Review failed.");
    } finally {
      setBusy(false);
    }
  }

  async function dispute() {
    if (!bookingId) return;
    setBusy(true);
    try {
      await api("/api/v1/bookings/" + bookingId + "/dispute", {
        method: "POST",
        body: JSON.stringify({reason: disputeReason}),
      });
      setMessage("The simulated completion dispute was opened for administrator review.");
      setDisputeReason("");
      await load();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Dispute could not be opened.");
    } finally {
      setBusy(false);
    }
  }

  return <Screen title="Completion & receipt" subtitle="All rescue and financial records on this screen are simulated.">
    <View style={styles.warning}><Text style={styles.warningText}>DEMO ONLY · NO LIVE RESCUE · NO REAL PAYMENT OR PAYOUT</Text></View>
    {!booking ? <Text>{message || "Loading protected completion…"}</Text> : <>
      <Card><Card.Content style={styles.stack}><Text variant="titleLarge" style={styles.title}>{booking.booking_reference}</Text><Text>{booking.status.replaceAll("_", " ")}</Text>{report ? <><Text variant="titleMedium">{report.outcome_label}</Text><Text>{report.observations}</Text><Text>{report.authorized_action_summary}</Text>{report.species_text ? <Text style={styles.caution}>Unverified species note: {report.species_text}</Text> : null}</> : <Text>No completion report is available.</Text>}{booking.status === "COMPLETED" && !booking.customer_confirmed_at ? <Button mode="contained" loading={busy} onPress={() => void confirm()}>Confirm demo completion</Button> : null}</Card.Content></Card>
      <Card><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>Private evidence metadata</Text><Text>Files remain private; exact evidence coordinates are withheld.</Text>{evidence.length ? evidence.map((item) => <View key={item.id} style={styles.evidence}><Text style={styles.bold}>{item.original_filename}</Text><Text>{item.evidence_type.replaceAll("_", " ")} · {Math.round(item.file_size / 1024)} KB</Text></View>) : <Text>No optional evidence attached.</Text>}</Card.Content></Card>
      {booking.customer_confirmed_at && !payment ? <Card><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>Demo payment choice</Text><SegmentedButtons value={method} onValueChange={(value) => {setMethod(value); if (value === "NO_CHARGE") setAmount("0.00");}} buttons={[{value:"NO_CHARGE",label:"No charge"},{value:"DEMO_ONLINE",label:"Online demo"},{value:"DEMO_CASH",label:"Cash demo"}]}/>{method !== "NO_CHARGE" ? <TextInput mode="outlined" label="Illustrative INR amount" keyboardType="decimal-pad" value={amount} onChangeText={setAmount}/> : null}<Button mode="contained" loading={busy} onPress={() => void pay()}>Save demo record</Button></Card.Content></Card> : null}
      {payment ? <Card><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>Demo receipt</Text><Text>{payment.payment_reference}</Text><Text>Status: {payment.status.replaceAll("_", " ")}</Text><Text>Illustrative amount: ₹{payment.amount}</Text><Text>Commission: {payment.commission_amount ? "₹" + payment.commission_amount : "not applicable"}</Text><Text style={styles.caution}>Not a tax invoice. No money moved.</Text></Card.Content></Card> : null}
      {booking.customer_confirmed_at ? <Card><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>Demo review</Text><SegmentedButtons value={rating} onValueChange={setRating} buttons={[1,2,3,4,5].map((value) => ({value:String(value),label:String(value)}))}/><TextInput mode="outlined" label="Comment (optional)" multiline value={review} onChangeText={setReview}/><Button mode="contained" loading={busy} onPress={() => void submitReview()}>Publish review</Button></Card.Content></Card> : null}
      {booking.status === "COMPLETED" ? <Card><Card.Content style={styles.stack}><Text variant="titleMedium" style={styles.title}>Report a completion issue</Text><Text>This opens a simulated dispute for restricted administrator review.</Text><TextInput mode="outlined" label="Reason" multiline value={disputeReason} onChangeText={setDisputeReason}/><Button mode="contained-tonal" disabled={disputeReason.trim().length < 10} loading={busy} onPress={() => void dispute()}>Open demo dispute</Button></Card.Content></Card> : null}
    </>}
    {message ? <Text style={styles.message}>{message}</Text> : null}
  </Screen>;
}

const styles = StyleSheet.create({
  warning:{backgroundColor:colors.danger,borderRadius:12,padding:14},
  warningText:{color:"white",fontWeight:"900",textAlign:"center",fontSize:12},
  stack:{gap:10},
  title:{fontWeight:"900",color:colors.forest},
  caution:{color:"#92400E",fontWeight:"700"},
  evidence:{backgroundColor:"#F1F5F9",borderRadius:10,padding:12},
  bold:{fontWeight:"800"},
  message:{fontWeight:"700",color:"#92400E"},
});
