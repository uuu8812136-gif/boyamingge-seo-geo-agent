import { randomUUID } from 'node:crypto';
import { createClient, type RedisClientType } from 'redis';

export type CustomerServiceSender = 'user' | 'bot' | 'agent' | 'system';
export type CustomerServiceStatus = 'bot' | 'waiting' | 'active' | 'closed';

export type CustomerServiceMessage = {
  id: string;
  sender: CustomerServiceSender;
  content: string;
  createdAt: string;
  author?: string;
};

export type CustomerServiceSession = {
  id: string;
  status: CustomerServiceStatus;
  source: 'main_site';
  pageUrl?: string;
  visitorLabel: string;
  handoffRequested: boolean;
  assignedTo?: string;
  createdAt: string;
  updatedAt: string;
  messages: CustomerServiceMessage[];
};

const GREETING = '你好，我是博雅敏格在线客服。可以问上门测量、报价、旧窗改造、阳台封窗、隔音窗，也可以随时转人工。';
const AUTO_CLOSE_MESSAGE = '超过5分钟没有新消息，会话已自动关闭。如需继续咨询，直接发送新消息即可重新开始。';
const MAX_MESSAGES_PER_SESSION = 120;
const MAX_SESSIONS = 200;
const DEFAULT_IDLE_TIMEOUT_MS = 5 * 60 * 1000;
const DEFAULT_CLOSED_RETENTION_MS = 30 * 60 * 1000;
const SESSION_SET_KEY = 'boyamingge:customer-service:sessions';
const SEQUENCE_KEY = 'boyamingge:customer-service:sequence';

const configuredIdleTimeout = Number(process.env.CUSTOMER_SERVICE_IDLE_TIMEOUT_MS);
const configuredClosedRetention = Number(process.env.CUSTOMER_SERVICE_CLOSED_RETENTION_MS);

export const CUSTOMER_SERVICE_IDLE_TIMEOUT_MS =
  Number.isFinite(configuredIdleTimeout) && configuredIdleTimeout > 0 ? configuredIdleTimeout : DEFAULT_IDLE_TIMEOUT_MS;
const CLOSED_SESSION_RETENTION_MS =
  Number.isFinite(configuredClosedRetention) && configuredClosedRetention > 0 ? configuredClosedRetention : DEFAULT_CLOSED_RETENTION_MS;
const SESSION_TTL_SECONDS = Math.ceil((CUSTOMER_SERVICE_IDLE_TIMEOUT_MS + CLOSED_SESSION_RETENTION_MS) / 1000) + 60;

type RedisGlobal = typeof globalThis & {
  __boyamingge_customer_service_redis__?: RedisClientType;
  __boyamingge_customer_service_memory__?: Map<string, CustomerServiceSession>;
  __boyamingge_customer_service_sequence__?: number;
};

function sessionKey(id: string) {
  return `boyamingge:customer-service:session:${id}`;
}

async function getRedis(): Promise<RedisClientType | null> {
  const globalObj = globalThis as RedisGlobal;
  if (!globalObj.__boyamingge_customer_service_redis__) {
    const client = createClient({
      url: process.env.REDIS_URL || 'redis://127.0.0.1:6379/1',
      socket: {
        connectTimeout: 3000,
        reconnectStrategy: (retries) => (retries >= 3 ? false : Math.min(250 * (retries + 1), 1000)),
      },
    });
    client.on('error', (error) => console.error('customer-service redis:', error));
    globalObj.__boyamingge_customer_service_redis__ = client as RedisClientType;
  }
  const client = globalObj.__boyamingge_customer_service_redis__;
  try {
    if (!client.isOpen) await client.connect();
    return client;
  } catch (error) {
    if (process.env.NODE_ENV === 'production') throw new Error(`客服 Redis 不可用：${error instanceof Error ? error.message : '连接失败'}`);
    return null;
  }
}

export async function customerServiceStoreHealth() {
  const redis = await getRedis();
  if (!redis) return { status: 'degraded', storage: 'memory' as const };
  const pong = await redis.ping();
  if (pong !== 'PONG') throw new Error('客服 Redis PING 失败');
  return { status: 'ready', storage: 'redis' as const };
}

function memoryStore() {
  const globalObj = globalThis as RedisGlobal;
  if (!globalObj.__boyamingge_customer_service_memory__) globalObj.__boyamingge_customer_service_memory__ = new Map();
  return globalObj.__boyamingge_customer_service_memory__;
}

async function nextSequence() {
  const redis = await getRedis();
  if (redis) return redis.incr(SEQUENCE_KEY);
  const globalObj = globalThis as RedisGlobal;
  globalObj.__boyamingge_customer_service_sequence__ = (globalObj.__boyamingge_customer_service_sequence__ || 0) + 1;
  return globalObj.__boyamingge_customer_service_sequence__;
}

function nowIso() {
  return new Date().toISOString();
}

function touch(session: CustomerServiceSession) {
  session.updatedAt = nowIso();
}

function appendMessage(session: CustomerServiceSession, sender: CustomerServiceSender, content: string, author?: string) {
  const text = content.trim();
  if (!text) return null;
  const message: CustomerServiceMessage = {
    id: `msg_${randomUUID()}`,
    sender,
    content: text.slice(0, 2000),
    createdAt: nowIso(),
    author,
  };
  session.messages.push(message);
  if (session.messages.length > MAX_MESSAGES_PER_SESSION) session.messages = session.messages.slice(-MAX_MESSAGES_PER_SESSION);
  touch(session);
  return message;
}

function timestampMs(value: string) {
  const time = new Date(value).getTime();
  return Number.isFinite(time) ? time : Date.now();
}

function closeIfIdle(session: CustomerServiceSession, now = Date.now()) {
  if (session.status === 'closed' || now - timestampMs(session.updatedAt) < CUSTOMER_SERVICE_IDLE_TIMEOUT_MS) return false;
  session.status = 'closed';
  session.assignedTo = undefined;
  appendMessage(session, 'system', AUTO_CLOSE_MESSAGE, '系统');
  return true;
}

async function saveSession(session: CustomerServiceSession) {
  const redis = await getRedis();
  if (redis) {
    await redis.multi()
      .set(sessionKey(session.id), JSON.stringify(session), { EX: SESSION_TTL_SECONDS })
      .sAdd(SESSION_SET_KEY, session.id)
      .exec();
    return;
  }
  memoryStore().set(session.id, structuredClone(session));
}

async function deleteSession(id: string) {
  const redis = await getRedis();
  if (redis) {
    await redis.multi().del(sessionKey(id)).sRem(SESSION_SET_KEY, id).exec();
    return;
  }
  memoryStore().delete(id);
}

async function loadSession(id: string): Promise<CustomerServiceSession | null> {
  const redis = await getRedis();
  if (redis) {
    const value = await redis.get(sessionKey(id));
    if (!value) {
      await redis.sRem(SESSION_SET_KEY, id);
      return null;
    }
    return JSON.parse(value) as CustomerServiceSession;
  }
  const value = memoryStore().get(id);
  return value ? structuredClone(value) : null;
}

export async function getOrCreateCustomerServiceSession(sessionId?: string | null, pageUrl?: string | null) {
  const existing = sessionId ? await loadSession(sessionId) : null;
  if (existing) {
    closeIfIdle(existing);
    if (pageUrl) existing.pageUrl = pageUrl;
    await saveSession(existing);
    return existing;
  }
  const sequence = await nextSequence();
  const createdAt = nowIso();
  const session: CustomerServiceSession = {
    id: `cs_${randomUUID()}`,
    status: 'bot',
    source: 'main_site',
    pageUrl: pageUrl || undefined,
    visitorLabel: `访客 ${String(sequence).padStart(3, '0')}`,
    handoffRequested: false,
    createdAt,
    updatedAt: createdAt,
    messages: [],
  };
  appendMessage(session, 'bot', GREETING, '智能客服');
  await saveSession(session);
  return session;
}

export async function getCustomerServiceSession(sessionId: string) {
  const session = await loadSession(sessionId);
  if (!session) return null;
  if (closeIfIdle(session)) await saveSession(session);
  return session;
}

export async function appendCustomerMessage(session: CustomerServiceSession, content: string) {
  if (session.status === 'closed') {
    session.status = 'bot';
    session.handoffRequested = false;
    session.assignedTo = undefined;
  }
  const result = appendMessage(session, 'user', content);
  await saveSession(session);
  return result;
}

export async function appendBotMessage(session: CustomerServiceSession, content: string) {
  const result = appendMessage(session, 'bot', content, '智能客服');
  await saveSession(session);
  return result;
}

export async function appendAgentMessage(session: CustomerServiceSession, content: string, author = '客服') {
  session.status = 'active';
  session.assignedTo = author;
  const result = appendMessage(session, 'agent', content, author);
  await saveSession(session);
  return result;
}

export async function markCustomerServiceHandoff(session: CustomerServiceSession) {
  session.handoffRequested = true;
  if (session.status !== 'active') session.status = 'waiting';
  touch(session);
  await saveSession(session);
}

export async function setCustomerServiceStatus(session: CustomerServiceSession, status: CustomerServiceStatus, author?: string) {
  session.status = status;
  if (author) session.assignedTo = author;
  touch(session);
  await saveSession(session);
  return session;
}

export async function listCustomerServiceSessions(status?: string | null) {
  const redis = await getRedis();
  const ids = redis ? await redis.sMembers(SESSION_SET_KEY) : Array.from(memoryStore().keys());
  const sessions = (await Promise.all(ids.map(loadSession))).filter((item): item is CustomerServiceSession => Boolean(item));
  const now = Date.now();
  for (const session of sessions) {
    if (closeIfIdle(session, now)) await saveSession(session);
    if (session.status === 'closed' && now - timestampMs(session.updatedAt) > CLOSED_SESSION_RETENTION_MS) await deleteSession(session.id);
  }
  const retained = sessions
    .filter((session) => !(session.status === 'closed' && now - timestampMs(session.updatedAt) > CLOSED_SESSION_RETENTION_MS))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  for (const old of retained.slice(MAX_SESSIONS)) await deleteSession(old.id);
  return retained.slice(0, MAX_SESSIONS).filter((session) => !status || status === 'all' || session.status === status);
}

export function serializeCustomerServiceSession(session: CustomerServiceSession) {
  const lastMessage = session.messages[session.messages.length - 1] || null;
  return {
    ...session,
    lastMessage,
    unreadUserCount: session.messages.filter((message) => message.sender === 'user').length,
  };
}

export async function getCustomerServiceSummary() {
  const sessions = await listCustomerServiceSessions('all');
  return {
    total: sessions.length,
    waiting: sessions.filter((session) => session.status === 'waiting').length,
    active: sessions.filter((session) => session.status === 'active').length,
    bot: sessions.filter((session) => session.status === 'bot').length,
    closed: sessions.filter((session) => session.status === 'closed').length,
  };
}
