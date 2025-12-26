// IndexedDB utility for chat history
// Provides: openDB, saveMessage, getMessages, listChats, deleteChat

const DB_NAME = 'ChatHistoryDB';
const DB_VERSION = 1;
const STORE_NAME = 'chats';

function openDB() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
        store.createIndex('userId', 'userId', { unique: false });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveMessage(userId: string, message: any) {
  const db = await openDB();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.add({ userId, ...message, timestamp: Date.now() });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getMessages(userId: string) {
  const db = await openDB();
  return new Promise<any[]>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const index = store.index('userId');
    const request = index.getAll(IDBKeyRange.only(userId));
    request.onsuccess = () => {
      // Sort by timestamp ascending
      resolve(request.result.sort((a, b) => a.timestamp - b.timestamp));
    };
    request.onerror = () => reject(request.error);
  });
}

export async function listChats() {
  const db = await openDB();
  return new Promise<{ userId: string; sessionId: string; lastMessage: any; }[]>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const index = store.index('userId');
    const sessionChats: Record<string, any[]> = {};
    index.openCursor().onsuccess = (event: any) => {
      const cursor = event.target.result;
      if (cursor) {
        const { userId, sessionId } = cursor.value;
        const key = userId + '_' + sessionId;
        if (!sessionChats[key]) sessionChats[key] = [];
        sessionChats[key].push(cursor.value);
        cursor.continue();
      } else {
        // For each session, get the last message
        const result = Object.entries(sessionChats).map(([key, messages]) => {
          const { userId, sessionId } = messages[0];
          return {
            userId,
            sessionId,
            lastMessage: messages.sort((a, b) => b.timestamp - a.timestamp)[0],
          };
        });
        resolve(result);
      }
    };
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteChat(userId: string) {
  const db = await openDB();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const index = store.index('userId');
    const request = index.openCursor(IDBKeyRange.only(userId));
    request.onsuccess = (event: any) => {
      const cursor = event.target.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      } else {
        resolve();
      }
    };
    tx.onerror = () => reject(tx.error);
  });
}

// Add a function to create a new chat session (even if empty)
export async function createChat(userId: string, sessionId: string) {
  const db = await openDB();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    // Insert a dummy message with a special flag and content to indicate empty chat
    store.add({ userId, sessionId, isEmpty: true, content: 'New Chat', timestamp: Date.now() });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
} 