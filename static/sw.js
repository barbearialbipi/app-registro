const CACHE_NAME = 'barbearia-v1'; // Mudei para v3 para garantir a atualização
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon_any_192.png',
  '/static/icons/icon_maskable_192.png',
  '/static/icons/icon_any_512.png',
  '/static/icons/icon_maskable_512.png'
];

// Instalação do Service Worker
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

// Busca (Fetch)
self.addEventListener('fetch', function(event) {
  event.respondWith(
    fetch(event.request).catch(function() {
      return caches.match(event.request);
    })
  );
});
