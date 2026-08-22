// sw.js — Service Worker

self.addEventListener('push', event => {
  let data = {};
  if (event.data) {
    try { data = event.data.json(); } catch { data = { title:'EmotiSense', body: event.data.text() }; }
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'EmotiSense Alert', {
      body:    data.body  || '',
      icon:    data.icon  || '/static/icons/icon-192.png',
      vibrate: [200, 100, 200],
      data:    data.data  || {},
      tag:     'emotisense-' + (data.data?.emotion || 'alert'),
      actions: [
        { action: 'open',    title: '📊 View results' },
        { action: 'dismiss', title: 'Dismiss' },
      ],
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action !== 'dismiss') {
    event.waitUntil(
      clients.matchAll({ type:'window', includeUncontrolled:true }).then(list => {
        for (const c of list) {
          if (c.url.includes('/demo') && 'focus' in c) return c.focus();
        }
        return clients.openWindow('/demo');
      })
    );
  }
});
