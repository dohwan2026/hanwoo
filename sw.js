// 한우 수첩 서비스 워커
// 캐시 우선: 우사 안처럼 신호가 약해도 바로 열리고, 뒤에서 최신 파일을 받아 다음 실행 때 반영한다.
// 날씨(open-meteo) 같은 다른 주소 요청은 건드리지 않는다.
const CACHE = 'hanwoo-v1';
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('hanwoo-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (new URL(e.request.url).origin !== location.origin) return;
  const update = fetch(e.request).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
    return res;
  });
  e.waitUntil(update.then(() => {}, () => {}));
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true })
      .then(r => r || (e.request.mode === 'navigate' ? caches.match('index.html') : undefined))
      .then(r => r || update)
  );
});
