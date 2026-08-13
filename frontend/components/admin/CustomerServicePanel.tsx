'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

type NoticeKind = 'success' | 'error' | 'info';

type CustomerServiceStatus = 'bot' | 'waiting' | 'active' | 'closed';

type CustomerServiceMessage = {
  id: string;
  sender: 'user' | 'bot' | 'agent' | 'system';
  content: string;
  createdAt: string;
  author?: string;
};

type CustomerServiceSession = {
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
  lastMessage?: CustomerServiceMessage | null;
  unreadUserCount?: number;
};

type CustomerServiceSummary = {
  total: number;
  waiting: number;
  active: number;
  bot: number;
  closed: number;
};

type Props = {
  token: string;
  showNotice: (message: string, kind?: NoticeKind) => void;
};

const STATUS_LABELS: Record<CustomerServiceStatus, string> = {
  waiting: '待接入',
  active: '人工中',
  bot: '机器人',
  closed: '已结束',
};

const FILTERS: Array<{ value: 'all' | CustomerServiceStatus; label: string }> = [
  { value: 'all', label: '全部会话' },
  { value: 'waiting', label: '待接入' },
  { value: 'active', label: '人工中' },
  { value: 'bot', label: '机器人' },
  { value: 'closed', label: '已结束' },
];

const QUICK_REPLIES = [
  '您好，我是博雅敏格人工客服。请问您所在城市、小区和大概需求是什么？',
  '可以的，建议先安排门店上门测量，报价会以现场尺寸和配置清单为准。',
  '请您留下手机号、城市和方便接听的时间，我们会安排对应门店回访。',
  '旧窗改造需要先确认原窗拆除、墙体收口和楼层情况，建议先预约测量。',
  '阳台封窗需要结合物业要求、楼层风压、排水和开启方式确认方案。',
  '如果现在方便，也可以直接拨打 400-888-6688 咨询。',
];

function formatTime(value?: string) {
  if (!value) return '-';
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value.slice(0, 16);
  }
}

function getMessagePreview(session: CustomerServiceSession) {
  const latest = session.lastMessage || session.messages?.[session.messages.length - 1];
  if (!latest) return '暂无消息';
  const prefix = latest.sender === 'user' ? '访客：' : latest.sender === 'agent' ? '客服：' : '机器人：';
  return `${prefix}${latest.content}`;
}

function getPageLabel(pageUrl?: string) {
  if (!pageUrl) return '总站';
  try {
    const url = new URL(pageUrl);
    return `${url.pathname || '/'} · 总站`;
  } catch {
    return '总站';
  }
}

export default function CustomerServicePanel({ token, showNotice }: Props) {
  const [filter, setFilter] = useState<'all' | CustomerServiceStatus>('all');
  const [summary, setSummary] = useState<CustomerServiceSummary>({ total: 0, waiting: 0, active: 0, bot: 0, closed: 0 });
  const [sessions, setSessions] = useState<CustomerServiceSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<CustomerServiceMessage[]>([]);
  const [reply, setReply] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeId) || null,
    [activeId, sessions],
  );

  const fetchSessions = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const response = await fetch(`/api/customer-service/admin?status=${encodeURIComponent(filter)}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`客服会话加载失败 ${response.status}`);
      const data = (await response.json()) as { summary: CustomerServiceSummary; sessions: CustomerServiceSession[] };
      setSummary(data.summary);
      setSessions(data.sessions || []);
      setActiveId((current) => {
        if (current && data.sessions?.some((session) => session.id === current)) return current;
        return data.sessions?.[0]?.id || null;
      });
    } catch (error) {
      if (!silent) showNotice(error instanceof Error ? error.message : '客服会话加载失败', 'error');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [filter, showNotice, token]);

  const fetchMessages = useCallback(async (sessionId: string, silent = true) => {
    try {
      const response = await fetch(`/api/customer-service/admin?sessionId=${encodeURIComponent(sessionId)}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`会话详情加载失败 ${response.status}`);
      const data = (await response.json()) as { session: CustomerServiceSession; messages: CustomerServiceMessage[] };
      setMessages(data.messages || []);
      setSessions((current) => current.map((item) => (item.id === data.session.id ? data.session : item)));
    } catch (error) {
      if (!silent) showNotice(error instanceof Error ? error.message : '会话详情加载失败', 'error');
    }
  }, [showNotice, token]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    fetchMessages(activeId, true);
  }, [activeId, fetchMessages]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      fetchSessions(true);
      if (activeId) fetchMessages(activeId, true);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [activeId, fetchMessages, fetchSessions]);

  const performAction = async (action: 'reply' | 'close' | 'reopen', message?: string) => {
    if (!activeId) return;
    setSending(true);
    try {
      const response = await fetch('/api/customer-service/admin', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ action, sessionId: activeId, message }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error?.error || `操作失败 ${response.status}`);
      }
      const data = (await response.json()) as { session: CustomerServiceSession; messages: CustomerServiceMessage[] };
      setMessages(data.messages || []);
      setSessions((current) => current.map((item) => (item.id === data.session.id ? data.session : item)));
      if (filter !== 'all' && filter !== data.session.status) {
        setFilter(data.session.status);
      } else {
        await fetchSessions(true);
      }
      showNotice(action === 'reply' ? '回复已发送' : action === 'close' ? '会话已结束' : '会话已重新打开', 'success');
    } catch (error) {
      showNotice(error instanceof Error ? error.message : '操作失败', 'error');
    } finally {
      setSending(false);
    }
  };

  const submitReply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = reply.trim();
    if (!text || sending) return;
    setReply('');
    performAction('reply', text);
  };

  return (
    <section className="admin-service-shell" aria-label="人工客服工作台">
      <div className="admin-service-overview" aria-label="客服会话概览">
        <div>
          <span>待接入</span>
          <strong>{summary.waiting}</strong>
        </div>
        <div>
          <span>人工中</span>
          <strong>{summary.active}</strong>
        </div>
        <div>
          <span>机器人</span>
          <strong>{summary.bot}</strong>
        </div>
        <div>
          <span>全部</span>
          <strong>{summary.total}</strong>
        </div>
      </div>

      <div className="admin-service-board">
        <aside className="admin-service-list" aria-label="会话列表">
          <div className="admin-service-list-head">
            <div>
              <h2>总站会话</h2>
              <p>前台左下角客服窗口进入</p>
            </div>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => fetchSessions()} disabled={loading}>
              {loading ? '刷新中' : '刷新'}
            </button>
          </div>

          <div className="admin-service-filters" role="tablist" aria-label="会话状态筛选">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={filter === item.value ? 'is-active' : ''}
                onClick={() => setFilter(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="admin-service-session-list">
            {sessions.length === 0 ? (
              <div className="admin-service-empty">
                <strong>暂无会话</strong>
                <p>访客点击“转人工”或继续留言后会出现在这里。</p>
              </div>
            ) : sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`admin-service-session${session.id === activeId ? ' is-active' : ''}`}
                onClick={() => setActiveId(session.id)}
              >
                <span className={`admin-service-status admin-service-status--${session.status}`}>
                  {STATUS_LABELS[session.status]}
                </span>
                <strong>{session.visitorLabel}</strong>
                <small>{formatTime(session.updatedAt)} · {getPageLabel(session.pageUrl)}</small>
                <p>{getMessagePreview(session)}</p>
              </button>
            ))}
          </div>
        </aside>

        <article className="admin-service-thread" aria-label="客服对话详情">
          {activeSession ? (
            <>
              <header className="admin-service-thread-head">
                <div>
                  <span className={`admin-service-status admin-service-status--${activeSession.status}`}>
                    {STATUS_LABELS[activeSession.status]}
                  </span>
                  <h2>{activeSession.visitorLabel}</h2>
                  <p>{getPageLabel(activeSession.pageUrl)} · 创建 {formatTime(activeSession.createdAt)}</p>
                </div>
                <div className="admin-service-thread-actions">
                  {activeSession.status === 'closed' ? (
                    <button type="button" className="btn btn-outline btn-sm" onClick={() => performAction('reopen')} disabled={sending}>重新打开</button>
                  ) : (
                    <button type="button" className="btn btn-outline btn-sm" onClick={() => performAction('close')} disabled={sending}>结束会话</button>
                  )}
                </div>
              </header>

              <div className="admin-service-messages" aria-live="polite">
                {messages.map((message) => (
                  <div key={message.id} className={`admin-service-message admin-service-message--${message.sender}`}>
                    <div className="admin-service-message-meta">
                      <span>{message.sender === 'user' ? '访客' : message.sender === 'agent' ? message.author || '人工客服' : '智能客服'}</span>
                      <time>{formatTime(message.createdAt)}</time>
                    </div>
                    <p>{message.content}</p>
                  </div>
                ))}
              </div>

              <div className="admin-service-quick-replies" aria-label="常用话术">
                {QUICK_REPLIES.map((item) => (
                  <button key={item} type="button" onClick={() => setReply(item)}>
                    {item}
                  </button>
                ))}
              </div>

              <form className="admin-service-composer" onSubmit={submitReply}>
                <label className="sr-only" htmlFor="service-reply">输入人工回复</label>
                <textarea
                  id="service-reply"
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="输入给访客的回复，Enter 可换行，点击发送提交"
                />
                <button className="btn btn-primary" type="submit" disabled={!reply.trim() || sending || activeSession.status === 'closed'}>
                  {sending ? '发送中…' : '发送回复'}
                </button>
              </form>
            </>
          ) : (
            <div className="admin-service-empty admin-service-empty--thread">
              <strong>请选择一个会话</strong>
              <p>客服在这里查看访客问题、发送回复、结束或重新打开会话。</p>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
