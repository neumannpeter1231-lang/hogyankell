/* Hogyankell service worker: értesítések fogadása és megnyitása. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.title || "Hogyankell", {
    body: d.body || "",
    icon: "/icons/icon-192.png",
    badge: "/icons/badge-96.png",
    tag: d.tag || "hogyankell",
    lang: "hu",
    data: { url: d.url || "/" }
  }));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "/", self.location.origin).href;
  e.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of list) {
      if (c.url.startsWith(self.location.origin)) { await c.focus(); if (c.navigate) await c.navigate(url); return; }
    }
    await self.clients.openWindow(url);
  })());
});
