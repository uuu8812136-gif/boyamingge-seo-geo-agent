'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { SITE } from '@/lib/site';
import {
  CUSTOMER_SERVICE_QUICK_QUESTIONS,
  getCustomerServiceFaqAnswer,
} from '@/lib/customer-service-faq';

type ChatRole = 'bot' | 'user';

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
};

type ApiMessage = {
  id: string;
  sender: 'user' | 'bot' | 'agent' | 'system';
  content: string;
  createdAt: string;
  author?: string;
};

type ApiSession = {
  id: string;
  status: 'bot' | 'waiting' | 'active' | 'closed';
};

const DEFAULT_GREETING = '你好，我是博雅敏格在线客服。可以问上门测量、报价、旧窗改造、阳台封窗、隔音窗，也可以随时转人工。';
const SESSION_STORAGE_KEY = 'boyamingge_cs_session_id';

function createMessage(role: ChatRole, content: string): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
  };
}

function localFallbackAnswer(message: string) {
  const text = message.trim();
  return getCustomerServiceFaqAnswer(text).answer;
}

function mapApiMessages(messages?: ApiMessage[]): ChatMessage[] {
  if (!messages?.length) return [createMessage('bot', DEFAULT_GREETING)];
  return messages.map((message) => ({
    id: message.id,
    role: message.sender === 'user' ? 'user' : 'bot',
    content:
      message.sender === 'agent'
        ? `${message.author || '人工客服'}：${message.content}`
        : message.content,
  }));
}

function getStatusText(status?: ApiSession['status']) {
  if (status === 'waiting') return '已转人工 · 等待客服接入';
  if (status === 'active') return '人工客服在线 · 当前会话中';
  if (status === 'closed') return '会话已结束 · 可继续留言';
  return '智能客服在线 · 可转人工';
}

export default function FloatingCustomerService() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [quickExpanded, setQuickExpanded] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<ApiSession['status']>('bot');
  const [messages, setMessages] = useState<ChatMessage[]>(() => [createMessage('bot', DEFAULT_GREETING)]);
  const pathname = usePathname();
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const isAdmin = pathname?.startsWith('/admin');

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(SESSION_STORAGE_KEY);
      if (saved) setSessionId(saved);
    } catch {
      // localStorage may be unavailable in private mode.
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    messagesEndRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, open]);

  useEffect(() => {
    if (!open || !sessionId) return;
    let stopped = false;

    const loadSession = async () => {
      try {
        const response = await fetch(`/api/customer-service/chat?sessionId=${encodeURIComponent(sessionId)}`, {
          cache: 'no-store',
        });
        if (!response.ok) return;
        const data = (await response.json()) as { session?: ApiSession; messages?: ApiMessage[] };
        if (stopped) return;
        if (data.session?.status) setSessionStatus(data.session.status);
        if (data.messages) setMessages(mapApiMessages(data.messages));
      } catch {
        // Keep the current local conversation when polling fails.
      }
    };

    loadSession();
    const timer = window.setInterval(loadSession, 3500);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [open, sessionId]);

  if (isAdmin) return null;

  const rememberSession = (id?: string) => {
    if (!id) return;
    setSessionId(id);
    try {
      window.localStorage.setItem(SESSION_STORAGE_KEY, id);
    } catch {
      // Ignore storage failures.
    }
  };

  const ask = async (rawText: string) => {
    const text = rawText.trim();
    if (!text || pending) return;

    const userMessage = createMessage('user', text);
    const nextHistory = [...messages, userMessage];
    setMessages(nextHistory);
    setInput('');
    setOpen(true);
    setPending(true);

    try {
      const response = await fetch('/api/customer-service/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          sessionId,
          pageUrl: window.location.href,
          history: nextHistory.slice(-8).map(({ role, content }) => ({ role, content })),
        }),
      });
      if (!response.ok) throw new Error(`chat api ${response.status}`);
      const data = (await response.json()) as {
        answer?: string;
        handoff?: boolean;
        sessionId?: string;
        session?: ApiSession;
        messages?: ApiMessage[];
      };
      rememberSession(data.sessionId || data.session?.id);
      if (data.session?.status) setSessionStatus(data.session.status);
      if (data.messages?.length) {
        setMessages(mapApiMessages(data.messages));
      } else {
        setMessages((current) => [...current, createMessage('bot', data.answer || localFallbackAnswer(text))]);
      }
    } catch {
      setMessages((current) => [...current, createMessage('bot', localFallbackAnswer(text))]);
    } finally {
      setPending(false);
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    ask(input);
  };

  const visibleQuickQuestions = quickExpanded
    ? CUSTOMER_SERVICE_QUICK_QUESTIONS
    : CUSTOMER_SERVICE_QUICK_QUESTIONS.slice(0, 2);

  return (
    <div className={`cs-widget ${open ? 'is-open' : ''}`} role="region" aria-label="在线客服聊天窗口">
      {open && (
        <div className="cs-panel" role="dialog" aria-label="在线客服对话框">
          <div className="cs-panel-head">
            <div>
              <span className="cs-eyebrow">在线客服</span>
              <strong>博雅敏格门窗顾问</strong>
              <p>机器人先答常见问题，复杂需求可转人工。</p>
            </div>
            <button
              className="cs-close"
              onClick={() => setOpen(false)}
              aria-label="收起客服对话框"
              type="button"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          <div className="cs-status" aria-label="服务状态">
            <span /> {getStatusText(sessionStatus)}
          </div>

          <div className="cs-messages" aria-live="polite">
            {messages.map((message) => (
              <div key={message.id} className={`cs-message cs-message--${message.role}`}>
                <span className="cs-avatar" aria-hidden>{message.role === 'bot' ? '窗' : '我'}</span>
                <div className="cs-bubble">{message.content}</div>
              </div>
            ))}
            {pending && (
              <div className="cs-message cs-message--bot">
                <span className="cs-avatar" aria-hidden>窗</span>
                <div className="cs-bubble cs-bubble--typing">
                  <i /> <i /> <i />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="cs-quick-section">
            <div className="cs-quick-list" aria-label="常见问题快捷入口">
              {visibleQuickQuestions.map((question) => (
                <button key={question} type="button" onClick={() => ask(question)} disabled={pending}>
                  {question}
                </button>
              ))}
            </div>
            <button
              className="cs-quick-more"
              type="button"
              onClick={() => setQuickExpanded((value) => !value)}
              aria-expanded={quickExpanded}
            >
              {quickExpanded ? '收起问题' : '查看更多问题'}
            </button>
          </div>

          <form className="cs-form" onSubmit={submit}>
            <label className="sr-only" htmlFor="cs-input">输入咨询内容</label>
            <input
              id="cs-input"
              className="cs-input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="输入问题，例如：阳台封窗怎么报价"
              autoComplete="off"
            />
            <button className="cs-send" type="submit" disabled={pending || !input.trim()} aria-label="发送消息">
              发送
            </button>
          </form>

          <div className="cs-actions">
            <button type="button" className="cs-agent-button" onClick={() => ask('转人工')} disabled={pending}>转人工</button>
            <a className="cs-hotline-mini" href={`tel:${SITE.hotline.replace(/-/g, '')}`}>拨打 {SITE.hotlineDisplay}</a>
          </div>
        </div>
      )}

      <button
        className="cs-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? '收起在线客服' : '打开在线客服'}
        aria-expanded={open}
        type="button"
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M5 5L15 15M15 5L5 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 10.5C5 7.46 7.69 5 11 5H13C16.31 5 19 7.46 19 10.5V12.5C19 15.54 16.31 18 13 18H11.3L7.5 20.2V17.4C6 16.5 5 14.72 5 12.5V10.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
            <path d="M9 11.5H15M9 14H12.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
        )}
        {!open && <span className="cs-toggle-label">客服</span>}
      </button>
    </div>
  );
}
