import { NextRequest, NextResponse } from 'next/server';
import {
  appendAgentMessage,
  getCustomerServiceSession,
  getCustomerServiceSummary,
  listCustomerServiceSessions,
  serializeCustomerServiceSession,
  setCustomerServiceStatus,
  type CustomerServiceStatus,
} from '@/lib/customer-service-store';

type AuthProfile = {
  username: string;
  role: string;
};

const VALID_STATUSES = new Set<CustomerServiceStatus>(['bot', 'waiting', 'active', 'closed']);

async function requireHeadquarterUser(request: NextRequest): Promise<AuthProfile | NextResponse> {
  const authorization = request.headers.get('authorization') || '';
  if (!authorization.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const apiBase = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  try {
    const response = await fetch(`${apiBase}/api/v1/auth/me`, {
      headers: { Authorization: authorization },
      cache: 'no-store',
    });
    if (!response.ok) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const profile = (await response.json()) as AuthProfile;
    if (profile.role !== 'admin' && profile.role !== 'operator') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }
    return profile;
  } catch {
    return NextResponse.json({ error: 'Auth service unavailable' }, { status: 503 });
  }
}

export async function GET(request: NextRequest) {
  const user = await requireHeadquarterUser(request);
  if (user instanceof NextResponse) return user;

  const status = request.nextUrl.searchParams.get('status') || 'all';
  const sessionId = request.nextUrl.searchParams.get('sessionId');
  if (sessionId) {
    const session = await getCustomerServiceSession(sessionId);
    if (!session) return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    return NextResponse.json({ session: serializeCustomerServiceSession(session), messages: session.messages });
  }

  return NextResponse.json({
    summary: await getCustomerServiceSummary(),
    sessions: (await listCustomerServiceSessions(status)).map(serializeCustomerServiceSession),
  });
}

export async function POST(request: NextRequest) {
  const user = await requireHeadquarterUser(request);
  if (user instanceof NextResponse) return user;

  let body: { action?: string; sessionId?: string; message?: string; status?: CustomerServiceStatus };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.sessionId) {
    return NextResponse.json({ error: 'sessionId is required' }, { status: 400 });
  }
  const session = await getCustomerServiceSession(body.sessionId);
  if (!session) return NextResponse.json({ error: 'Session not found' }, { status: 404 });

  if (body.action === 'reply') {
    if (!body.message?.trim()) {
      return NextResponse.json({ error: 'message is required' }, { status: 400 });
    }
    await appendAgentMessage(session, body.message, user.username || '客服');
  } else if (body.action === 'close') {
    await setCustomerServiceStatus(session, 'closed', user.username);
  } else if (body.action === 'reopen') {
    await setCustomerServiceStatus(session, 'active', user.username);
  } else if (body.action === 'status' && body.status && VALID_STATUSES.has(body.status)) {
    await setCustomerServiceStatus(session, body.status, user.username);
  } else {
    return NextResponse.json({ error: 'Unsupported action' }, { status: 400 });
  }

  return NextResponse.json({ session: serializeCustomerServiceSession(session), messages: session.messages });
}
