// Service Worker for 꿀템장바구니 PWA
// Enhanced version with security, performance, and offline improvements

// BUILD_TIME is updated automatically during deployment
const BUILD_TIME = '2026-02-10T02:02:10.616Z';
const CACHE_VERSION = 'v7-' + BUILD_TIME.replace(/[^0-9]/g, '').slice(0, 12);
const CACHE_NAME = `honeycart-${CACHE_VERSION}`;
const DATA_CACHE = `honeycart-data-${CACHE_VERSION}`;
const IMAGE_CACHE = `honeycart-images-v1`; // Version-independent for better hit rates

// All static assets including all icons from manifest.json
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icon-72.png',
  '/icon-96.png',
  '/icon-128.png',
  '/icon-144.png',
  '/icon-152.png',
  '/icon-192.png',
  '/icon-384.png',
  '/icon-512.png',
];

// Data files for offline support
const DATA_ASSETS = [
  '/data/daiso.json',
  '/data/costco.json',
  '/data/ikea.json',
  '/data/oliveyoung.json',
  '/data/traders.json',
  '/data/convenience.json',
  '/data/summary.json',
  '/data/youtube_products.json',
];

// Image cache settings
const IMAGE_CACHE_MAX_ITEMS = 200;
const IMAGE_CACHE_MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days

// Trusted image domains (explicit allowlist for security)
const TRUSTED_IMAGE_HOSTS = [
  'i.ytimg.com', 'i1.ytimg.com', 'i2.ytimg.com',
  'i3.ytimg.com', 'i4.ytimg.com', 'img.youtube.com'
];

// Security: Check if response is cacheable (no opaque responses)
function isCacheableResponse(response) {
  if (!response || !response.ok) return false;
  // Only cache same-origin or properly CORS-validated responses
  if (response.type === 'opaque') return false;
  return response.type === 'basic' || response.type === 'cors';
}

// Security: Sanitize text for notifications
function sanitizeText(text, maxLength = 200) {
  if (typeof text !== 'string') return '';
  return text.slice(0, maxLength).replace(/[<>]/g, '');
}

// Security: Validate URL is same-origin
function validateSameOriginUrl(urlString) {
  if (!urlString) return '/';
  try {
    const parsedUrl = new URL(urlString, self.location.origin);
    if (parsedUrl.origin === self.location.origin) {
      return parsedUrl.pathname + parsedUrl.search;
    }
  } catch (e) {}
  return '/';
}

// Install event with improved error handling
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...', CACHE_VERSION);
  event.waitUntil(
    Promise.all([
      // Static assets cache
      caches.open(CACHE_NAME).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS).catch((err) => {
          console.warn('[SW] Some static assets failed to cache:', err.message);
        });
      }),
      // Data files cache with individual error handling
      caches.open(DATA_CACHE).then((cache) => {
        console.log('[SW] Caching data files');
        return Promise.allSettled(
          DATA_ASSETS.map(url =>
            cache.add(url).catch(err => {
              console.warn(`[SW] Failed to cache ${url}:`, err.message);
            })
          )
        );
      }),
    ])
  );
  // Don't skipWaiting here - let client control update timing
});

// Activate event with proper waitUntil and navigation preload
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...', CACHE_VERSION);
  event.waitUntil(
    (async () => {
      // Enable navigation preload if supported
      if ('navigationPreload' in self.registration) {
        try {
          await self.registration.navigationPreload.enable();
        } catch (e) {}
      }

      // Get all cache names
      const cacheNames = await caches.keys();
      const ourCaches = cacheNames.filter(name => name.startsWith('honeycart'));
      const currentCaches = [CACHE_NAME, DATA_CACHE, IMAGE_CACHE];
      const oldCaches = ourCaches.filter(name => !currentCaches.includes(name));

      // Delete old caches
      await Promise.all(
        oldCaches.map(name => {
          console.log('[SW] Deleting old cache:', name);
          return caches.delete(name);
        })
      );

      // Clean expired images
      await cleanExpiredImages();

      // Notify clients of update
      const clients = await self.clients.matchAll();
      clients.forEach((client) => {
        client.postMessage({
          type: 'SW_UPDATED',
          version: CACHE_VERSION,
        });
      });

      // Take control of all clients
      await self.clients.claim();
    })()
  );
});

// Fetch event with security improvements
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Security: Only handle GET requests
  if (request.method !== 'GET') return;

  // Security: Skip range requests (for media streaming)
  if (request.headers.get('range')) return;

  // Handle cross-origin image requests (with allowlist)
  if (isImageRequest(request) && url.origin !== location.origin) {
    if (isTrustedImageHost(url.hostname)) {
      event.respondWith(cacheFirstWithRuntimeCaching(request));
    }
    return;
  }

  // Block other cross-origin requests from SW handling
  if (url.origin !== location.origin) return;

  // Data files - Stale-While-Revalidate
  if (url.pathname.startsWith('/data/') && url.pathname.endsWith('.json')) {
    event.respondWith(staleWhileRevalidate(request, DATA_CACHE));
    return;
  }

  // API requests - Network First with structured offline response
  if (url.pathname.startsWith('/api')) {
    event.respondWith(networkFirst(request, DATA_CACHE));
    return;
  }

  // Same-origin images
  if (isImageRequest(request)) {
    event.respondWith(cacheFirstWithRuntimeCaching(request));
    return;
  }

  // Static assets - Stale-While-Revalidate
  event.respondWith(staleWhileRevalidate(request, CACHE_NAME));
});

// Check if hostname is in trusted list
function isTrustedImageHost(hostname) {
  return TRUSTED_IMAGE_HOSTS.includes(hostname) ||
         TRUSTED_IMAGE_HOSTS.some(h => hostname.endsWith('.' + h));
}

// Image request detection (security-improved)
function isImageRequest(request) {
  const url = new URL(request.url);

  // Check file extensions (most reliable)
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico'];
  if (imageExtensions.some(ext => url.pathname.toLowerCase().endsWith(ext))) return true;

  // Local image paths
  if (url.pathname.startsWith('/images/') && url.origin === location.origin) return true;

  // Trusted external image domains
  if (isTrustedImageHost(url.hostname)) return true;

  return false;
}

// Cache First with Runtime Caching (security-enhanced)
async function cacheFirstWithRuntimeCaching(request) {
  const cache = await caches.open(IMAGE_CACHE);
  const cached = await cache.match(request);

  if (cached) return cached;

  try {
    const response = await fetch(request);

    // Security: Only cache valid, non-opaque responses
    if (isCacheableResponse(response)) {
      // Validate Content-Type for images
      const contentType = response.headers.get('Content-Type') || '';
      const validImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml', 'image/x-icon'];

      if (validImageTypes.some(type => contentType.startsWith(type))) {
        const clone = response.clone();
        limitCacheSize(IMAGE_CACHE, IMAGE_CACHE_MAX_ITEMS).then(() => {
          cache.put(request, clone);
        });
      }
    }

    return response;
  } catch (error) {
    // Offline placeholder with security headers
    return new Response(
      '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect fill="#f3f4f6" width="100" height="100"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="#9ca3af" font-size="12">Offline</text></svg>',
      {
        status: 200,
        headers: {
          'Content-Type': 'image/svg+xml',
          'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'",
          'X-Content-Type-Options': 'nosniff',
          'Cache-Control': 'no-store'
        }
      }
    );
  }
}

// Enhanced cache size limit with LRU-like behavior and expiration
async function limitCacheSize(cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  const now = Date.now();

  // Collect metadata for smarter eviction
  const entries = await Promise.all(
    keys.map(async (request) => {
      const response = await cache.match(request);
      const dateHeader = response?.headers.get('date');
      const cacheTime = dateHeader ? new Date(dateHeader).getTime() : 0;
      return { request, cacheTime, isExpired: (now - cacheTime) > IMAGE_CACHE_MAX_AGE };
    })
  );

  // Delete expired items first
  const expiredEntries = entries.filter(e => e.isExpired);
  await Promise.all(expiredEntries.map(({ request }) => cache.delete(request)));

  // Then check count limit (sort by age, delete oldest)
  const remainingKeys = await cache.keys();
  if (remainingKeys.length > maxItems) {
    const validEntries = entries.filter(e => !e.isExpired);
    validEntries.sort((a, b) => a.cacheTime - b.cacheTime);
    const deleteCount = remainingKeys.length - maxItems;
    await Promise.all(
      validEntries.slice(0, deleteCount).map(({ request }) => cache.delete(request))
    );
  }
}

// Clean expired images (called during activate)
async function cleanExpiredImages() {
  try {
    const cache = await caches.open(IMAGE_CACHE);
    const keys = await cache.keys();
    const now = Date.now();

    await Promise.all(
      keys.map(async (request) => {
        const response = await cache.match(request);
        const dateHeader = response?.headers.get('date');
        if (dateHeader) {
          const cacheTime = new Date(dateHeader).getTime();
          if (now - cacheTime > IMAGE_CACHE_MAX_AGE) {
            await cache.delete(request);
          }
        }
      })
    );
  } catch (e) {
    console.warn('[SW] Error cleaning expired images:', e);
  }
}

// Network First with freshness headers and structured offline response
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);

    if (isCacheableResponse(response)) {
      const cache = await caches.open(cacheName);

      // Clone and add freshness header
      const headers = new Headers(response.headers);
      headers.set('X-SW-Cached-At', new Date().toISOString());
      headers.set('X-SW-Cache-Status', 'fresh');

      const enhancedResponse = new Response(response.clone().body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
      });

      cache.put(request, enhancedResponse.clone());
      return enhancedResponse;
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);

    if (cached) {
      console.log('[SW] Serving from cache (offline):', request.url);

      // Add stale indicator
      const headers = new Headers(cached.headers);
      headers.set('X-SW-Cache-Status', 'stale');

      return new Response(cached.body, {
        status: cached.status,
        statusText: cached.statusText,
        headers: headers
      });
    }

    // Return structured offline response matching API format
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/products')) {
      return new Response(JSON.stringify({
        products: [],
        total: 0,
        offline: true,
        message: '오프라인 상태입니다. 연결 복구 시 데이터가 갱신됩니다.'
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-SW-Cache-Status': 'offline-empty',
          'X-Content-Type-Options': 'nosniff'
        }
      });
    }

    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff'
      }
    });
  }
}

// Stale-While-Revalidate with proper caching check
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Background revalidation
  const networkPromise = fetch(request).then((response) => {
    if (isCacheableResponse(response)) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);

  // Return cached immediately if available
  if (cached) return cached;

  // Wait for network if no cache
  const networkResponse = await networkPromise;
  if (networkResponse) return networkResponse;

  // Offline fallback
  return new Response('오프라인 상태입니다', {
    status: 503,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'X-Content-Type-Options': 'nosniff'
    }
  });
}

// Message handler with source validation
self.addEventListener('message', (event) => {
  // Security: Validate message source
  if (!event.source || event.source.type !== 'window') return;

  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data === 'CLEAR_IMAGE_CACHE') {
    caches.delete(IMAGE_CACHE).then(() => {
      console.log('[SW] Image cache cleared');
    });
  }

  if (event.data === 'REFRESH_DATA') {
    refreshDataCache().then(() => {
      event.source?.postMessage({ type: 'DATA_REFRESHED' });
    });
  }
});

// Refresh data cache (for background sync)
async function refreshDataCache() {
  const cache = await caches.open(DATA_CACHE);

  await Promise.allSettled(
    DATA_ASSETS.map(async (url) => {
      try {
        const response = await fetch(url, { cache: 'no-store' });
        if (response.ok) {
          await cache.put(url, response);
        }
      } catch (e) {}
    })
  );
}

// Background Sync support
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync event:', event.tag);

  if (event.tag === 'sync-products' || event.tag === 'refresh-data') {
    event.waitUntil(refreshDataCache());
  }
});

// Push notification with security sanitization
self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch (err) {
    console.warn('[SW] Invalid push data');
    data = { title: '꿀템장바구니', body: '새로운 알림이 있습니다' };
  }

  // Security: Sanitize and validate
  const safeUrl = validateSameOriginUrl(data.url);
  const safeTitle = sanitizeText(data.title) || '꿀템장바구니';
  const safeBody = sanitizeText(data.body) || '새로운 상품이 추가되었습니다!';

  const options = {
    body: safeBody,
    icon: '/icon-192.png',
    badge: '/icon-72.png',
    vibrate: [100, 50, 100],
    data: { url: safeUrl },
    actions: [
      { action: 'open', title: '확인하기' },
      { action: 'close', title: '닫기' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(safeTitle, options)
  );
});

// Notification click with URL validation
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'open' || !event.action) {
    // Security: Validate URL is same-origin
    const url = validateSameOriginUrl(event.notification.data?.url);

    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((windowClients) => {
        for (const client of windowClients) {
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
    );
  }
});
