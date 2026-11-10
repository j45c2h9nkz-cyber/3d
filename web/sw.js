// Offline-Speicher der 3D-Ansichten: mit Verbindung immer der neueste Stand, ohne Verbindung (oder nach 4 s) der gespeicherte.
// __STAND__ und __DATEIEN__ setzt werkzeuge/bauen.py bei jedem Bau neu.
var STAND = "dreid-__STAND__";
var DATEIEN = __DATEIEN__;

self.addEventListener("install", function(e){
  e.waitUntil(caches.open(STAND)
    .then(function(c){ return c.addAll(DATEIEN.map(function(u){ return new Request(u, {cache: "reload"}); })); })
    .then(function(){ return self.skipWaiting(); }));
});

self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys()
    // Unter derselben Adresse liegen weitere Apps (Statik, Ski, Cockpit) mit eigenem Speicher: nur die eigenen alten Staende loeschen
    .then(function(namen){ return Promise.all(namen.filter(function(n){ return n.indexOf("dreid-") === 0 && n !== STAND; }).map(function(n){ return caches.delete(n); })); })
    .then(function(){ return self.clients.claim(); }));
});

self.addEventListener("fetch", function(e){
  var anfrage = e.request;
  if(anfrage.method !== "GET" || new URL(anfrage.url).origin !== location.origin) return;
  var eintrag = anfrage.mode === "navigate" ? "./" : anfrage;
  var netz = caches.open(STAND).then(function(c){
    return fetch(anfrage, {cache: "no-cache"}).then(function(r){ if(r.ok) return c.put(eintrag, r.clone()).then(function(){ return r; }); return r; });
  });
  function gespeichert(){ return caches.open(STAND).then(function(c){ return c.match(eintrag, {ignoreSearch: true}); }); }
  e.waitUntil(netz.catch(function(){}));
  e.respondWith(Promise.race([
    netz,
    new Promise(function(ok){ setTimeout(ok, 4000); }).then(function(){ return gespeichert().then(function(t){ return t || netz; }); })
  ]).catch(function(){ return gespeichert().then(function(t){ return t || Response.error(); }); }));
});
