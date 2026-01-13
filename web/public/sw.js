// Service Worker for 꿀템장바구니 PWA
const CACHE_VERSION = 'v2';
const CACHE_NAME = `honeycart-${CACHE_VERSION}`;
const DATA_CACHE = `honeycart-data-${CACHE_VERSION}`;
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// 데이터 파일 (오프라인 시 필수)
const DATA_ASSETS = [
  '/data/daiso.json',
  '/data/costco.json',
  '/data/ikea.json',
  '/data/oliveyoung.json',
  '/data/traders.json',
  '/data/convenience.json',
  '/data/summary.json',
];

// 설치 이벤트
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    Promise.all([
      // 정적 자산 캐시
      caches.open(CACHE_NAME).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      }),
      // 데이터 파일 캐시 (오프라인 지원)
      caches.open(DATA_CACHE).then((cache) => {
        console.log('[SW] Caching data files for offline use');
        return cache.addAll(DATA_ASSETS).catch((err) => {
          console.log('[SW] Some data files not cached:', err);
        });
      }),
    ])
  );
  self.skipWaiting();
});

// 활성화 이벤트
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== DATA_CACHE)
          .filter((name) => name.startsWith('honeycart'))
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// 페치 이벤트
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 같은 origin만 처리
  if (url.origin !== location.origin) {
    return;
  }

  // 데이터 파일 (/data/*.json) - Stale-While-Revalidate 전략
  if (url.pathname.startsWith('/data/') && url.pathname.endsWith('.json')) {
    event.respondWith(staleWhileRevalidate(request, DATA_CACHE));
    return;
  }

  // API 요청 - Network First 전략
  if (url.pathname.startsWith('/api')) {
    event.respondWith(networkFirst(request, DATA_CACHE));
    return;
  }

  // 정적 자산 - Stale-While-Revalidate 전략
  event.respondWith(staleWhileRevalidate(request, CACHE_NAME));
});

// Network First 전략 (항상 최신 데이터 시도)
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Serving from cache (offline):', request.url);
      return cached;
    }
    return new Response(JSON.stringify({ error: 'Offline', products: [] }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Stale-While-Revalidate 전략 (캐시 먼저 반환, 백그라운드 업데이트)
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // 백그라운드에서 네트워크 요청
  const networkPromise = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);

  // 캐시가 있으면 즉시 반환
  if (cached) {
    return cached;
  }

  // 캐시 없으면 네트워크 응답 대기
  const networkResponse = await networkPromise;
  if (networkResponse) {
    return networkResponse;
  }

  // 오프라인 폴백
  return new Response('오프라인 상태입니다', {
    status: 503,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' }
  });
}

// 푸시 알림 수신
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body || '새로운 상품이 추가되었습니다!',
    icon: '/icon-192.png',
    badge: '/icon-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
    },
    actions: [
      { action: 'open', title: '확인하기' },
      { action: 'close', title: '닫기' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || '꿀템장바구니', options)
  );
});

// 알림 클릭 처리
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'open' || !event.action) {
    const url = event.notification.data?.url || '/';
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((windowClients) => {
        // 이미 열려있는 탭이 있으면 포커스
        for (const client of windowClients) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        // 없으면 새 탭 열기
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
    );
  }
});
