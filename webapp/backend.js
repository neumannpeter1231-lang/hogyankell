/* Hogyankell – zárt webapp: belépés, meghívólista, adatbázis és értesítések (Supabase).
   Az app kódja (app.js) ugyanaz, mint a prototípusé; ez a fájl adja alá a „backend”-et. */
(function () {
  "use strict";
  const C = window.HOGYANKELL_CONFIG || {};
  const gate = document.getElementById("gate");
  const LOGO = '<div class="g-logo" aria-hidden="true"><svg viewBox="0 0 24 24" width="46" height="46" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l10 5-10 5L2 7z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>';
  const GOOGLE = '<svg viewBox="0 0 48 48" width="20" height="20" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.6-.4-3.5z"/></svg>';
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function show(html) { gate.innerHTML = html; gate.hidden = false; document.body.classList.add("locked"); }

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

  if (!C.supabaseUrl || !C.supabaseKey || /IDE_/.test(C.supabaseUrl + C.supabaseKey) || !window.supabase) {
    show(`${LOGO}<h1>Még nincs beállítva</h1><p>A config.js fájlban hiányzik a Supabase címe vagy kulcsa, vagy nem töltött be a Supabase. Nézd át az útmutató 4. lépését.</p>`);
    return;
  }

  const sb = window.supabase.createClient(C.supabaseUrl, C.supabaseKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: "pkce" }
  });

  function showLogin(msg) {
    show(`${LOGO}<h1>Hogyankell</h1>
      <p>Gyakorlati tudás, rövid videókban.</p>
      <p class="g-muted">Zárt teszt: csak meghívott e-mail címmel lehet belépni.</p>
      ${msg ? `<p class="g-err">${esc(msg)}</p>` : ""}
      <button class="g-btn" id="gGoogle">${GOOGLE}<span>Belépés Google-fiókkal</span></button>`);
    document.getElementById("gGoogle").onclick = async () => {
      const keep = new URLSearchParams(location.search).get("kod");
      const back = location.origin + "/" + (keep ? "?kod=" + encodeURIComponent(keep) : "");
      const { error } = await sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: back } });
      if (error) showLogin("A Google-belépést most nem sikerült elindítani. Próbáld újra.");
    };
  }

  function showNotInvited(email) {
    show(`${LOGO}<h1>Ez egy zárt teszt</h1>
      <p>A(z) <b>${esc(email)}</b> cím még nincs a meghívottak között.</p>
      <p class="g-muted">Szólj annak, aki meghívott, hogy vegyen fel a listára, aztán nyomd meg az „Újra” gombot.</p>
      <div class="g-row"><button class="g-btn" id="gRetry">Újra</button><button class="g-btn alt" id="gOther">Másik fiókkal lépek be</button></div>`);
    document.getElementById("gRetry").onclick = () => location.reload();
    document.getElementById("gOther").onclick = async () => { await sb.auth.signOut(); showLogin(); };
  }

  function showError() {
    show(`${LOGO}<h1>Most nem érjük el a szervert</h1><p class="g-muted">Ellenőrizd a netet, és próbáld újra.</p><button class="g-btn" id="gRetry">Újra</button>`);
    document.getElementById("gRetry").onclick = () => location.reload();
  }

  async function start() {
    show(`${LOGO}<p class="g-muted">Betöltés…</p>`);
    let session = null;
    try { ({ data: { session } } = await sb.auth.getSession()); } catch (e) { return showError(); }
    if (location.search.includes("code=") || location.hash.includes("access_token")) {
      const kod = new URLSearchParams(location.search).get("kod");
      history.replaceState(null, "", "/" + (kod ? "?kod=" + encodeURIComponent(kod) : ""));
    }
    if (!session) return showLogin();
    const { data: member, error } = await sb.rpc("is_member");
    if (error) return showError();
    if (!member) return showNotInvited(session.user.email);
    await ensureProfile(session.user);
    launch(session.user);
  }

  async function ensureProfile(u) {
    const md = u.user_metadata || {};
    const name = (md.full_name || md.name || (u.email || "").split("@")[0] || "Játékos").slice(0, 60);
    try { await sb.from("profiles").upsert({ id: u.id, name, updated_at: new Date().toISOString() }, { onConflict: "id" }); } catch (e) {}
  }

  /* ---------- a prototípus „claude.use()” felületének megfelelője ---------- */
  const collOf = path => path.slice(0, path.lastIndexOf("/"));
  const lastSeg = path => path.slice(path.lastIndexOf("/") + 1);
  function makeDb() {
    const doc = path => ({
      async get() {
        const { data, error } = await sb.from("docs").select("data").eq("path", path).maybeSingle();
        if (error) throw error;
        return { exists: !!data, id: lastSeg(path), data: () => (data ? data.data : undefined) };
      },
      async set(obj) {
        const { error } = await sb.from("docs").upsert({ path, coll: collOf(path), data: obj, updated_at: new Date().toISOString() }, { onConflict: "path" });
        if (error) throw error;
      },
      async update(obj) {
        const keys = Object.keys(obj);
        if (path.startsWith("challenges/") && keys.length === 1 && keys[0].startsWith("r_")) {
          const v = obj[keys[0]] || {};
          const { error } = await sb.rpc("challenge_result", { p_code: lastSeg(path), p_score: Number(v.s) || 0 });
          if (error) throw error;
          return;
        }
        const cur = await this.get();
        await this.set(Object.assign({}, cur.data() || {}, obj));
      }
    });
    const run = async q => {
      const { data, error } = await q;
      if (error) throw error;
      return { docs: (data || []).map(r => ({ id: lastSeg(r.path), data: () => r.data })) };
    };
    const collection = path => ({
      where(field, op, value) {
        return { get: () => run(sb.from("docs").select("path, data").eq("coll", path).eq("data->>" + field, String(value)).limit(500)) };
      },
      get: () => run(sb.from("docs").select("path, data").eq("coll", path).limit(500))
    });
    return { doc, collection };
  }

  function makeUser(u) {
    return {
      id: async () => u.id,
      me: async () => ({ id: u.id, name: ((u.user_metadata || {}).full_name || "") }),
      isOwner: () => false,
      async profiles(ids) {
        const out = {};
        (ids || []).forEach(i => { out[i] = { name: "" }; });
        if (!ids || !ids.length) return out;
        const { data } = await sb.from("profiles").select("id, name").in("id", ids);
        (data || []).forEach(r => { out[r.id] = { name: r.name || "" }; });
        return out;
      }
    };
  }

  const downloads = {
    async save({ filename, data }) {
      const blob = data instanceof Blob ? data : new Blob([data]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = filename || "hogyankell"; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return { status: "saved" };
    }
  };

  function b64ToU8(b64) {
    const pad = "=".repeat((4 - (b64.length % 4)) % 4);
    const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, c => c.charCodeAt(0));
  }
  function makePush(u) {
    return {
      async enable() {
        const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
        const standalone = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
        if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
          return { ok: false, msg: ios && !standalone ? "iPhone-on előbb tedd ki az appot a kezdőképernyőre (Megosztás → Főképernyőhöz adás), és onnan nyisd meg." : "Ez a böngésző nem tud értesítést fogadni." };
        }
        if (!C.vapidPublicKey || /IDE_/.test(C.vapidPublicKey)) return { ok: false, msg: "Az értesítések még nincsenek beállítva." };
        const perm = await Notification.requestPermission();
        if (perm !== "granted") return { ok: false, msg: "Az értesítést a telefon vagy a böngésző beállításaiban tudod engedélyezni." };
        const reg = await navigator.serviceWorker.ready;
        let sub = await reg.pushManager.getSubscription();
        if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(C.vapidPublicKey) });
        const json = sub.toJSON();
        const { error } = await sb.from("push_subs").upsert({ endpoint: json.endpoint, user_id: u.id, sub: json }, { onConflict: "endpoint" });
        if (error) return { ok: false, msg: "Az értesítést most nem sikerült elmenteni." };
        return { ok: true };
      },
      async sync(payload) {
        const p = Object.assign({}, payload || {});
        const tz = p.tz || "Europe/Budapest"; delete p.tz;
        await sb.from("reminders").upsert({ user_id: u.id, tz, cfg: p, updated_at: new Date().toISOString() }, { onConflict: "user_id" });
      }
    };
  }

  function launch(u) {
    window.HOGYANKELL_URL = location.origin + "/";
    const caps = { db: makeDb(), user: makeUser(u), downloads, push: makePush(u) };
    window.claude = { use: async name => caps[name] || null };
    gate.hidden = true; gate.innerHTML = ""; document.body.classList.remove("locked");
    const s = document.createElement("script");
    s.src = "/app.js?v=" + encodeURIComponent(C.version || "1");
    s.onload = () => addLogout(u);
    document.body.appendChild(s);
  }

  function addLogout(u) {
    const host = document.querySelector("#v-profil .scroll"); if (!host) return;
    const box = document.createElement("div");
    box.className = "card stack"; box.style.gap = "8px";
    box.innerHTML = `<div class="eyebrow">Fiók</div><div class="small muted">Belépve: ${esc(u.email || "")}</div><button class="linkbtn" id="gLogout" style="align-self:flex-start">Kijelentkezés</button>`;
    host.appendChild(box);
    document.getElementById("gLogout").onclick = async () => { try { localStorage.removeItem("hogyankell-v1"); } catch (e) {} await sb.auth.signOut(); location.href = "/"; };
  }

  start();
})();
