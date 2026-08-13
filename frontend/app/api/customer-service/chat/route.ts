import { NextRequest, NextResponse } from 'next/server';
import { getCustomerServiceFaqAnswer } from '@/lib/customer-service-faq';
import {
  appendBotMessage,
  appendCustomerMessage,
  getCustomerServiceSession,
  getOrCreateCustomerServiceSession,
  markCustomerServiceHandoff,
  serializeCustomerServiceSession,
} from '@/lib/customer-service-store';

export const runtime = 'nodejs';

type ChatRole = 'bot' | 'user' | 'assistant' | 'system';

type ChatMessage = {
  role: ChatRole;
  content: string;
};

type ChatRequest = {
  message?: string;
  history?: ChatMessage[];
  sessionId?: string;
  pageUrl?: string;
};

const SYSTEM_PROMPT = '你是博雅敏格门窗官网在线客服，回答系统门窗、阳台封窗、旧窗改造、隔音窗、防盗门、上门测量和门店预约相关问题。回答要简洁、务实；不能确定价格时提醒以门店实测为准；用户要求人工时引导拨打 400-888-6688 或留下联系方式。';

function normalizeHistory(history: ChatMessage[] = []) {
  return (Array.isArray(history) ? history : [])
    .filter((item) => item && typeof item.content === 'string')
    .slice(-8)
    .map((item) => ({
      role: item.role === 'bot' ? 'assistant' : item.role === 'user' ? 'user' : item.role,
      content: item.content.slice(0, 800),
    }));
}

async function askConfiguredModel(body: ChatRequest) {
  const apiUrl = process.env.AI_CUSTOMER_SERVICE_API_URL;
  if (!apiUrl || !body.message) return null;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (process.env.AI_CUSTOMER_SERVICE_API_KEY) {
    headers.Authorization = `Bearer ${process.env.AI_CUSTOMER_SERVICE_API_KEY}`;
  }

  const payload = {
    model: process.env.AI_CUSTOMER_SERVICE_MODEL || 'customer-service-default',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      ...normalizeHistory(body.history),
      { role: 'user', content: body.message.slice(0, 1000) },
    ],
  };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  let response: Response;
  try {
    response = await fetch(apiUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      cache: 'no-store',
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) throw new Error(`AI customer service API ${response.status}`);
  const data = await response.json();
  const answer = data?.answer || data?.message || data?.choices?.[0]?.message?.content || data?.choices?.[0]?.text;
  if (!answer || typeof answer !== 'string') return null;
  return { answer, intent: data?.intent || 'ai', handoff: Boolean(data?.handoff), source: 'ai' };
}

export async function GET(request: NextRequest) {
  const sessionId = request.nextUrl.searchParams.get('sessionId');
  if (!sessionId) {
    return NextResponse.json({ error: 'sessionId is required' }, { status: 400 });
  }
  const session = await getCustomerServiceSession(sessionId);
  if (!session) {
    return NextResponse.json({ error: 'Session not found' }, { status: 404 });
  }
  return NextResponse.json({ session: serializeCustomerServiceSession(session), messages: session.messages });
}

export async function POST(request: NextRequest) {
  let body: ChatRequest;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const message = typeof body.message === 'string' ? body.message.trim() : '';
  if (!message) {
    return NextResponse.json({ error: 'Message is required' }, { status: 400 });
  }

  const session = await getOrCreateCustomerServiceSession(body.sessionId, body.pageUrl?.slice(0, 500));
  await appendCustomerMessage(session, message);

  const wantsHuman = /人工|转人工|真人|客服|电话|联系|回电/.test(message);
  if (wantsHuman) {
    await markCustomerServiceHandoff(session);
    const answer = getCustomerServiceFaqAnswer(message);
    await appendBotMessage(session, answer.answer);
    return NextResponse.json({
      ...answer,
      sessionId: session.id,
      session: serializeCustomerServiceSession(session),
      messages: session.messages,
    });
  }

  if (session.status === 'waiting' || session.status === 'active') {
    return NextResponse.json({
      answer: '已收到，人工客服会在当前对话里继续回复。',
      intent: 'human_queue',
      handoff: true,
      source: 'human_queue',
      sessionId: session.id,
      session: serializeCustomerServiceSession(session),
      messages: session.messages,
    });
  }

  try {
    const modelAnswer = await askConfiguredModel({ ...body, message });
    if (modelAnswer) {
      await appendBotMessage(session, modelAnswer.answer);
      if (modelAnswer.handoff) await markCustomerServiceHandoff(session);
      return NextResponse.json({
        ...modelAnswer,
        sessionId: session.id,
        session: serializeCustomerServiceSession(session),
        messages: session.messages,
      });
    }
  } catch (error) {
    console.warn('AI customer service fallback:', error);
  }

  const answer = getCustomerServiceFaqAnswer(message);
  if (answer.handoff) await markCustomerServiceHandoff(session);
  await appendBotMessage(session, answer.answer);
  return NextResponse.json({
    ...answer,
    sessionId: session.id,
    session: serializeCustomerServiceSession(session),
    messages: session.messages,
  });
}
