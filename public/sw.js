// In your app JS:
navigator.serviceWorker.controller.postMessage({ type: 'FORCE_SYNC' });
navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' }); // for update prompts
// With reply:
const ch = new MessageChannel();
ch.port1.onmessage = e => console.log('Queue:', e.data.count);
navigator.serviceWorker.controller.postMessage({ type: 'GET_QUEUE_COUNT' }, [ch.port2]);
