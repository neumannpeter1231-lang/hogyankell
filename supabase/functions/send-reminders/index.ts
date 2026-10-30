// Hogyankell – emlékeztetők küldése (Supabase Edge Function, neve: send-reminders)
// 5 percenként hívja az időzítő (3_idozito.sql). Megnézi, kinek esedékes a napi
// kérdés vagy egy szokás-emlékeztető, és elküldi a telefonjára.
import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2.117.3";

const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("SERVICE_KEY") ?? "";
const supa = createClient(Deno.env.get("SUPABASE_URL") ?? "", SERVICE_KEY, { auth: { persistSession: false } });

// A titkokat levágjuk (szóköz, sortörés), mert bemásoláskor könnyen a végükre kerül egy.
const env = (n: string) => (Deno.env.get(n) ?? "").trim();
webpush.setVapidDetails(
  env("VAPID_SUBJECT") || "mailto:hogyankell@example.com",
  env("VAPID_PUBLIC_KEY"),
  env("VAPID_PRIVATE_KEY"),
);

// Ha az időzítő egy ideig nem futott, ennyi percen belül még kiküldjük, utána már nem (ne éjjel jöjjön).
const WINDOW_MIN = 60;

function localNow(tz: string, d = new Date()) {
  const f = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  });
  const p: Record<string, string> = {};
  for (const x of f.formatToParts(d)) p[x.type] = x.value;
  return { date: `${p.year}-${p.month}-${p.day}`, mins: Number(p.hour) * 60 + Number(p.minute) };
}
const toMin = (hm: string) => {
  const [h, m] = String(hm || "0:0").split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
};
const isDue = (nowMin: number, hm: string) => {
  const t = toMin(hm);
  return nowMin >= t && nowMin - t < WINDOW_MIN;
};

type Habit = { id: string; text: string; time: string; start: string; end: string; logged?: string | null };
type Cfg = { daily?: string | null; dailyQ?: string; habits?: Habit[] };

export function messagesFor(cfg: Cfg, sentIn: Record<string, string>, now: { date: string; mins: number }) {
  const sent = { ...(sentIn || {}) };
  const msgs: { title: string; body: string; tag: string }[] = [];
  if (cfg.daily && sent.daily !== now.date && isDue(now.mins, cfg.daily)) {
    msgs.push({ title: "Hogyankell: 1 kérdés vár rád", body: cfg.dailyQ || "Nézz be egy percre, és ismételj!", tag: "daily" });
    sent.daily = now.date;
  }
  for (const h of cfg.habits || []) {
    const key = "h_" + h.id;
    if (h.logged === now.date) continue;
    if (now.date < h.start || now.date > h.end) continue;
    if (sent[key] === now.date || !isDue(now.mins, h.time)) continue;
    msgs.push({ title: "A vállalásod", body: h.text, tag: key });
    sent[key] = now.date;
  }
  for (const k of Object.keys(sent)) if (sent[k] !== now.date) delete sent[k];
  return { msgs, sent };
}

Deno.serve(async (req) => {
  if ((req.headers.get("x-cron-secret") ?? "").trim() !== env("CRON_SECRET")) {
    return new Response("forbidden", { status: 403 });
  }
  const { data: rows, error } = await supa.from("reminders").select("user_id, tz, cfg, sent");
  if (error) return new Response(error.message, { status: 500 });

  let delivered = 0, failed = 0;
  for (const r of rows ?? []) {
    let now;
    try { now = localNow(r.tz || "Europe/Budapest"); } catch { now = localNow("Europe/Budapest"); }
    const { msgs, sent } = messagesFor(r.cfg || {}, r.sent || {}, now);
    if (!msgs.length) continue;
    const { data: subs } = await supa.from("push_subs").select("endpoint, sub").eq("user_id", r.user_id);
    for (const s of subs ?? []) {
      for (const m of msgs) {
        try {
          await webpush.sendNotification(s.sub, JSON.stringify({ ...m, url: "/" }), { TTL: 3600 });
          delivered++;
        } catch (e) {
          failed++;
          const code = (e as { statusCode?: number })?.statusCode;
          if (code === 404 || code === 410) await supa.from("push_subs").delete().eq("endpoint", s.endpoint);
        }
      }
    }
    await supa.from("reminders").update({ sent }).eq("user_id", r.user_id);
  }
  return new Response(JSON.stringify({ ok: true, delivered, failed }), { headers: { "Content-Type": "application/json" } });
});
