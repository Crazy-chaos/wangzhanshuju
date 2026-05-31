const CACHE_NAME = 'taffy-site-v1';
// 我们只缓存网页骨架，视频太大会导致浏览器卡顿或存储超限，所以视频通过 server.py 的 HTTP 缓存处理
const urlsToCache = [
  './',
  './index.html'
];

// 安装 Service Worker 并缓存网页
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// 拦截网络请求，实现离线/弱网秒开
self.addEventListener('fetch', event => {
  // 对于视频和压缩包，我们直接从网络获取（配合 HTTP Cache），不走 SW 缓存池
  if (event.request.url.endsWith('.mp4') || event.request.url.endsWith('.zip')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // 如果在缓存中找到匹配的响应，直接返回（秒开网页）
        if (response) {
          return response;
        }
        // 否则去网络请求
        return fetch(event.request);
      })
  );
});
