'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { adminFetch } from '@/lib/api';
import { API_BASE } from '@/lib/site';
import AdminStatusPill from './AdminStatusPill';

type PlatformInfo = {
  code: number;
  name: string;
  display: string;
  supported: boolean;
  tier: string; // verified | beta | planned
  can_publish: boolean;
  note: string;
};

type ExternalAccount = {
  id: number;
  platform: string;
  platform_code: number;
  display_name: string;
  cookie_status: string;
  last_login_at: string | null;
  status: string;
  city: string | null;
  note: string | null;
  created_at: string | null;
};

type PublishTask = {
  id: number;
  content_id: number;
  platform: string;
  social_account_id: number;
  title: string;
  status: string;
  error_message: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
};

type PublishLog = {
  id: number;
  task_id: number;
  level: string;
  message: string;
  created_at: string | null;
};

type PublishArtifact = {
  id: number;
  task_id: number;
  artifact_type: string;
  filename: string;
  url: string | null;
  note: string | null;
  created_at: string | null;
};

type ContentMaterial = {
  id: number;
  content_id: number | null;
  filename: string;
  file_type: string;
  url: string | null;
  cover_url: string | null;
  size_mb: number | null;
  duration_sec: number | null;
  status: string;
  created_at: string | null;
};

// 需要绑定视频素材的短视频平台
const VIDEO_PLATFORM_NAMES = new Set(['channels', 'douyin', 'kuaishou', 'bilibili']);
const isVideoPlatform = (name: string) => VIDEO_PLATFORM_NAMES.has(name);

type Props = {
  token: string;
  showNotice: (msg: string, kind?: 'success' | 'error' | 'info') => void;
};

const COOKIE_STATUS_LABELS: Record<string, string> = {
  active: '有效',
  expired: '已过期',
  missing_cookie: '未登录',
  disabled: '已禁用',
};

const COOKIE_STATUS_TONES: Record<string, 'good' | 'bad' | 'warn' | 'neutral'> = {
  active: 'good',
  expired: 'bad',
  missing_cookie: 'warn',
  disabled: 'neutral',
};

const TASK_STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  scheduled: '定时待发',
  queued: '已派发',
  running: '执行中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消',
};

const TASK_STATUS_TONES: Record<string, 'neutral' | 'info' | 'good' | 'bad' | 'warn'> = {
  pending: 'neutral',
  scheduled: 'info',
  queued: 'info',
  running: 'info',
  success: 'good',
  failed: 'bad',
  cancelled: 'warn',
};

const PLATFORM_DISPLAY: Record<string, string> = {
  xiaohongshu: '小红书',
  baijiahao: '百家号',
  zhihu: '知乎',
  douyin: '抖音',
  kuaishou: '快手',
  bilibili: 'B站',
  channels: '视频号',
};

const TIER_LABELS: Record<string, string> = {
  verified: '已验证',
  beta: '可用未实测',
  planned: '待接入',
};

const TIER_TONES: Record<string, 'good' | 'warn' | 'neutral'> = {
  verified: 'good',
  beta: 'warn',
  planned: 'neutral',
};

/** 外部平台分发：账号管理 + 扫码登录 + 发布任务 + 执行日志。 */
export default function ExternalDistributionPanel({ token, showNotice }: Props) {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [accounts, setAccounts] = useState<ExternalAccount[]>([]);
  const [tasks, setTasks] = useState<PublishTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskFilter, setTaskFilter] = useState('');
  // 新建账号
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [newAccount, setNewAccount] = useState({ platform: 'xiaohongshu', display_name: '', city: '', note: '' });
  // 扫码登录
  const [loginSession, setLoginSession] = useState<{ session_id: string; qr_image: string; platform: string } | null>(null);
  const [loginStatus, setLoginStatus] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // 新建发布任务
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [taskForm, setTaskForm] = useState({ content_id: '', platform: 'xiaohongshu', account_id: '', title: '', description: '', topics: '', publish_mode: 'direct', scheduled_at: '' });
  // 日志 + 截图留痕
  const [logs, setLogs] = useState<PublishLog[]>([]);
  const [artifacts, setArtifacts] = useState<PublishArtifact[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [logsTaskId, setLogsTaskId] = useState<number | null>(null);
  // 视频素材（短视频平台发布必备）
  const [contentVideos, setContentVideos] = useState<ContentMaterial[]>([]);
  const [videoUploading, setVideoUploading] = useState(false);
  const videoInputRef = useRef<HTMLInputElement | null>(null);

  const loadPlatforms = useCallback(async () => {
    try {
      const data = await adminFetch<{ items: PlatformInfo[] }>(`/api/v1/external-accounts/platforms`, token);
      setPlatforms(data.items || []);
    } catch {
      // 静默
    }
  }, [token]);

  const loadAccounts = useCallback(async () => {
    try {
      const data = await adminFetch<{ items: ExternalAccount[]; total: number }>(`/api/v1/external-accounts`, token);
      setAccounts(data.items || []);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载账号失败', 'error');
    }
  }, [token, showNotice]);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (taskFilter) params.set('status', taskFilter);
      params.set('page', '1');
      params.set('page_size', '30');
      const data = await adminFetch<{ items: PublishTask[]; total: number }>(
        `/api/v1/publish/tasks?${params}`,
        token,
      );
      setTasks(data.items || []);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载任务失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [token, showNotice, taskFilter]);

  useEffect(() => {
    loadPlatforms();
    loadAccounts();
    loadTasks();
  }, [loadPlatforms, loadAccounts, loadTasks]);

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const addAccount = async () => {
    if (!newAccount.display_name.trim()) {
      showNotice('请输入账号名称', 'error');
      return;
    }
    try {
      await adminFetch(`/api/v1/external-accounts`, token, {
        method: 'POST',
        body: JSON.stringify({
          platform: newAccount.platform,
          display_name: newAccount.display_name,
          city: newAccount.city || null,
          note: newAccount.note || null,
        }),
      });
      showNotice('账号已添加，请扫码登录', 'success');
      setShowAddAccount(false);
      setNewAccount({ platform: 'xiaohongshu', display_name: '', city: '', note: '' });
      loadAccounts();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '添加失败', 'error');
    }
  };

  const deleteAccount = async (row: ExternalAccount) => {
    if (!confirm(`确认删除账号「${row.display_name}」？关联的 cookie 也会清除。`)) return;
    try {
      await adminFetch(`/api/v1/external-accounts/${row.id}`, token, { method: 'DELETE' });
      showNotice('账号已删除', 'info');
      loadAccounts();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '删除失败', 'error');
    }
  };

  const startLogin = async (row: ExternalAccount) => {
    try {
      const data = await adminFetch<{ session_id: string; qr_image: string; qr_url: string; platform: string }>(
        `/api/v1/external-accounts/${row.id}/login`,
        token,
        { method: 'POST' },
      );
      setLoginSession({ session_id: data.session_id, qr_image: data.qr_image, platform: data.platform });
      setLoginStatus('waiting');
      // 开始轮询
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const status = await adminFetch<{ status: string; message: string }>(
            `/api/v1/external-accounts/login/status?session_id=${data.session_id}`,
            token,
          );
          setLoginStatus(status.status);
          if (status.status === 'confirmed') {
            if (pollRef.current) clearInterval(pollRef.current);
            showNotice('登录成功，cookie 已保存', 'success');
            setLoginSession(null);
            loadAccounts();
          } else if (status.status === 'expired' || status.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            showNotice(status.message || '登录失败或二维码已过期', 'error');
          }
        } catch {
          // 轮询失败，忽略
        }
      }, 3000);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '启动登录失败', 'error');
    }
  };

  const checkCookie = async (row: ExternalAccount) => {
    try {
      const data = await adminFetch<{ status: string; valid?: boolean; message?: string }>(
        `/api/v1/external-accounts/${row.id}/check`,
        token,
        { method: 'POST' },
      );
      if (data.status === 'active') {
        showNotice(`${row.display_name} cookie 有效`, 'success');
      } else if (data.status === 'expired') {
        showNotice(`${row.display_name} cookie 已过期，请重新登录`, 'error');
      } else {
        showNotice(data.message || data.status, 'info');
      }
      loadAccounts();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '检测失败', 'error');
    }
  };

  const createTask = async () => {
    if (!taskForm.content_id || !taskForm.account_id) {
      showNotice('请填写内容 ID 和选择账号', 'error');
      return;
    }
    if (taskForm.publish_mode === 'schedule' && !taskForm.scheduled_at) {
      showNotice('定时发布请选择发布时间', 'error');
      return;
    }
    if (isVideoPlatform(taskForm.platform) && contentVideos.length === 0) {
      showNotice('短视频平台需先为该内容上传/绑定视频素材', 'error');
      return;
    }
    try {
      await adminFetch(`/api/v1/publish/tasks`, token, {
        method: 'POST',
        body: JSON.stringify({
          content_id: Number(taskForm.content_id),
          platform: taskForm.platform,
          account_id: Number(taskForm.account_id),
          title: taskForm.title || null,
          description: taskForm.description || null,
          topics: taskForm.topics ? taskForm.topics.split(',').map((t) => t.trim()).filter(Boolean) : [],
          publish_mode: taskForm.publish_mode,
          scheduled_at: taskForm.publish_mode === 'schedule' && taskForm.scheduled_at
            ? new Date(taskForm.scheduled_at).toISOString()
            : null,
        }),
      });
      showNotice(taskForm.publish_mode === 'schedule' ? '定时发布任务已登记' : '发布任务已创建', 'success');
      setShowCreateTask(false);
      setTaskForm({ content_id: '', platform: 'xiaohongshu', account_id: '', title: '', description: '', topics: '', publish_mode: 'direct', scheduled_at: '' });
      setContentVideos([]);
      loadTasks();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '创建任务失败', 'error');
    }
  };

  const retryTask = async (row: PublishTask) => {
    try {
      await adminFetch(`/api/v1/publish/tasks/${row.id}/retry`, token, { method: 'POST' });
      showNotice('任务已重新派发', 'info');
      loadTasks();
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '重试失败', 'error');
    }
  };

  const viewLogs = async (row: PublishTask) => {
    try {
      const data = await adminFetch<{ items: PublishLog[]; total: number }>(
        `/api/v1/publish/tasks/${row.id}/logs`,
        token,
      );
      setLogs(data.items || []);
      setLogsTaskId(row.id);
      setShowLogs(true);
      try {
        const art = await adminFetch<{ items: PublishArtifact[]; total: number }>(
          `/api/v1/publish/tasks/${row.id}/artifacts`,
          token,
        );
        setArtifacts(art.items || []);
      } catch {
        setArtifacts([]);
      }
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '加载日志失败', 'error');
    }
  };

  const loadContentVideos = useCallback(async (contentId: string) => {
    if (!contentId) {
      setContentVideos([]);
      return;
    }
    try {
      const data = await adminFetch<{ items: ContentMaterial[]; total: number }>(
        `/api/v1/content/${contentId}/materials?file_type=video`,
        token,
      );
      setContentVideos(data.items || []);
    } catch {
      setContentVideos([]);
    }
  }, [token]);

  // 打开新建任务且为视频平台时，随内容 ID 变化加载已绑定视频素材
  useEffect(() => {
    if (showCreateTask && isVideoPlatform(taskForm.platform) && taskForm.content_id) {
      loadContentVideos(taskForm.content_id);
    } else {
      setContentVideos([]);
    }
  }, [showCreateTask, taskForm.platform, taskForm.content_id, loadContentVideos]);

  const uploadContentVideo = async (file: File) => {
    if (!taskForm.content_id) {
      showNotice('请先填写内容 ID 再上传视频', 'error');
      return;
    }
    setVideoUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API_BASE}/api/v1/content/${taskForm.content_id}/materials/video`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `上传失败 ${res.status}`);
      }
      showNotice('视频素材已上传并绑定内容', 'success');
      await loadContentVideos(taskForm.content_id);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '视频上传失败', 'error');
    } finally {
      setVideoUploading(false);
      if (videoInputRef.current) videoInputRef.current.value = '';
    }
  };

  const deleteContentVideo = async (material: ContentMaterial) => {
    if (!confirm(`确认移除视频素材「${material.filename}」？`)) return;
    try {
      await adminFetch(`/api/v1/content/${material.content_id}/materials/${material.id}`, token, { method: 'DELETE' });
      showNotice('视频素材已移除', 'info');
      await loadContentVideos(taskForm.content_id);
    } catch (e) {
      showNotice(e instanceof Error ? e.message : '移除失败', 'error');
    }
  };

  const accountOptionsForPlatform = accounts.filter((a) => a.platform === taskForm.platform);
  const needVideo = isVideoPlatform(taskForm.platform);
  const hasVideo = contentVideos.length > 0;

  return (
    <div className="admin-stack">
      <div className="admin-guide-banner">
        <strong>外部平台分发</strong>
        <p>通过网页自动化将内容发布到小红书、百家号、知乎、视频号、抖音、快手、B站等平台。支持扫码登录、cookie 管理、发布任务队列、失败重试、执行日志与截图留痕。</p>
        <ol className="admin-step-flow">
          <li>添加账号并<b>扫码登录</b>（cookie 有效才能发布）</li>
          <li>图文平台自动取内容封面/素材图；<b>短视频平台</b>需先在「内容」里绑定视频素材</li>
          <li>新建任务选平台/账号，<b>立即或定时</b>发布</li>
          <li>失败可看<b>日志与截图</b>并一键重试</li>
        </ol>
      </div>

      {/* 平台能力总览 */}
      <section className="admin-card">
        <div className="admin-card-body">
          <h2>平台能力</h2>
          <div className="admin-platform-grid">
            {platforms.map((pf) => (
              <div
                key={pf.name}
                className={`admin-platform-card${pf.tier === 'planned' ? ' is-planned' : ''}`}
              >
                <div className="admin-platform-name">{pf.display}</div>
                <span className={`admin-tier-badge admin-tier-badge--${pf.tier}`}>
                  {TIER_LABELS[pf.tier] || pf.tier}
                </span>
                <p className="admin-platform-note">{pf.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 账号管理 */}
      <section className="admin-card">
        <div className="admin-card-body">
          <div className="admin-toolbar">
            <h2>外部账号</h2>
            <button className="btn btn-primary btn-sm" type="button" onClick={() => setShowAddAccount(true)}>+ 添加账号</button>
          </div>
          {accounts.length === 0 ? (
            <p className="admin-empty">暂无外部账号，请先添加账号并扫码登录。</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>平台</th>
                  <th>账号名称</th>
                  <th>Cookie状态</th>
                  <th>城市</th>
                  <th>最近登录</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{PLATFORM_DISPLAY[row.platform] || row.platform}</td>
                    <td>{row.display_name}</td>
                    <td><AdminStatusPill tone={COOKIE_STATUS_TONES[row.cookie_status] || 'neutral'}>{COOKIE_STATUS_LABELS[row.cookie_status] || row.cookie_status}</AdminStatusPill></td>
                    <td>{row.city || '-'}</td>
                    <td>{row.last_login_at ? row.last_login_at.slice(0, 16) : '-'}</td>
                    <td>
                      <div className="admin-row-actions">
                        {row.cookie_status !== 'active' && (
                          <button className="btn btn-primary btn-sm" type="button" onClick={() => startLogin(row)}>扫码登录</button>
                        )}
                        <button className="btn btn-outline btn-sm" type="button" onClick={() => checkCookie(row)}>检测Cookie</button>
                        <button className="btn btn-outline btn-sm" type="button" onClick={() => deleteAccount(row)}>删除</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* 发布任务 */}
      <section className="admin-card">
        <div className="admin-card-body">
          <div className="admin-toolbar">
            <h2>发布任务</h2>
            <div className="admin-toolbar-controls">
              <select value={taskFilter} onChange={(e) => setTaskFilter(e.target.value)}>
                <option value="">全部状态</option>
                <option value="pending">排队中</option>
                <option value="scheduled">定时待发</option>
                <option value="queued">已派发</option>
                <option value="running">执行中</option>
                <option value="success">成功</option>
                <option value="failed">失败</option>
                <option value="cancelled">已取消</option>
              </select>
              <button className="btn btn-outline btn-sm" type="button" disabled={loading} onClick={loadTasks}>刷新</button>
              <button className="btn btn-primary btn-sm" type="button" onClick={() => setShowCreateTask(true)}>+ 新建任务</button>
            </div>
          </div>
          {tasks.length === 0 ? (
            <p className="admin-empty">暂无发布任务。</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>内容ID</th>
                  <th>平台</th>
                  <th>标题</th>
                  <th>状态</th>
                  <th>错误信息</th>
                  <th>时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.content_id}</td>
                    <td>{PLATFORM_DISPLAY[row.platform] || row.platform}</td>
                    <td className="admin-cell-title">{row.title}</td>
                    <td><AdminStatusPill tone={TASK_STATUS_TONES[row.status] || 'neutral'}>{TASK_STATUS_LABELS[row.status] || row.status}</AdminStatusPill></td>
                    <td className="admin-cell-error">{row.error_message || '-'}</td>
                    <td>{row.finished_at ? row.finished_at.slice(0, 16) : row.created_at ? row.created_at.slice(0, 16) : '-'}</td>
                    <td>
                      <div className="admin-row-actions">
                        {row.status === 'failed' && (
                          <button className="btn btn-primary btn-sm" type="button" onClick={() => retryTask(row)}>重试</button>
                        )}
                        <button className="btn btn-outline btn-sm" type="button" onClick={() => viewLogs(row)}>日志</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* 添加账号弹窗 */}
      {showAddAccount && (
        <div className="admin-modal-overlay" onClick={() => setShowAddAccount(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <h3>添加外部账号</h3>
            <label>平台
              <select value={newAccount.platform} onChange={(e) => setNewAccount({ ...newAccount, platform: e.target.value })}>
                {platforms.map((pf) => <option key={pf.name} value={pf.name}>{pf.display}（{TIER_LABELS[pf.tier] || pf.tier}）</option>)}
              </select>
            </label>
            <label>账号名称<input value={newAccount.display_name} onChange={(e) => setNewAccount({ ...newAccount, display_name: e.target.value })} placeholder="如：广州门店小红书号" /></label>
            <label>城市（可选）<input value={newAccount.city} onChange={(e) => setNewAccount({ ...newAccount, city: e.target.value })} placeholder="广州" /></label>
            <label>备注（可选）<input value={newAccount.note} onChange={(e) => setNewAccount({ ...newAccount, note: e.target.value })} /></label>
            <div className="admin-form-actions">
              <button className="btn btn-primary" type="button" onClick={addAccount}>添加</button>
              <button className="btn btn-outline" type="button" onClick={() => setShowAddAccount(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {/* 扫码登录弹窗 */}
      {loginSession && (
        <div className="admin-modal-overlay" onClick={() => { setLoginSession(null); if (pollRef.current) clearInterval(pollRef.current); }}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <h3>扫码登录 — {PLATFORM_DISPLAY[loginSession.platform] || loginSession.platform}</h3>
            <p className="admin-card-note">请使用平台 App 扫描下方二维码完成登录。</p>
            {loginSession.qr_image && (
              <div className="admin-qr-wrap">
                <img src={loginSession.qr_image} alt="登录二维码" />
              </div>
            )}
            <div className="admin-login-status">
              状态：<AdminStatusPill tone={loginStatus === 'confirmed' ? 'good' : loginStatus === 'expired' || loginStatus === 'failed' ? 'bad' : 'info'}>{loginStatus}</AdminStatusPill>
            </div>
            <div className="admin-form-actions">
              <button className="btn btn-outline" type="button" onClick={() => { setLoginSession(null); if (pollRef.current) clearInterval(pollRef.current); }}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* 新建发布任务弹窗 */}
      {showCreateTask && (
        <div className="admin-modal-overlay" onClick={() => setShowCreateTask(false)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <h3>新建发布任务</h3>
            <label>内容 ID<input value={taskForm.content_id} onChange={(e) => setTaskForm({ ...taskForm, content_id: e.target.value })} placeholder="站内内容 ID" /></label>
            <label>平台
              <select
                value={taskForm.platform}
                onChange={(e) => setTaskForm({ ...taskForm, platform: e.target.value, account_id: '' })}
              >
                {platforms.filter((pf) => pf.can_publish).map((pf) => (
                  <option key={pf.name} value={pf.name}>{pf.display}（{TIER_LABELS[pf.tier] || pf.tier}）</option>
                ))}
              </select>
            </label>
            <label>账号
              <select value={taskForm.account_id} onChange={(e) => setTaskForm({ ...taskForm, account_id: e.target.value })}>
                <option value="">选择账号</option>
                {accountOptionsForPlatform.map((a) => (
                  <option key={a.id} value={a.id}>{a.display_name}{a.cookie_status === 'active' ? '（已登录）' : '（未登录）'}</option>
                ))}
              </select>
            </label>
            <label>标题（可选）<input value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="不填则使用内容标题" /></label>
            <label>描述（可选）<textarea rows={3} value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} /></label>
            <label>话题标签（逗号分隔）<input value={taskForm.topics} onChange={(e) => setTaskForm({ ...taskForm, topics: e.target.value })} placeholder="防盗门, 装修" /></label>
            {needVideo && (
              <div className="admin-video-section">
                <div className="admin-video-head">
                  <span>视频素材（{PLATFORM_DISPLAY[taskForm.platform] || taskForm.platform} 发布必备）</span>
                  <input
                    ref={videoInputRef}
                    type="file"
                    accept="video/*"
                    style={{ display: 'none' }}
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadContentVideo(f); }}
                  />
                  <button
                    className="btn btn-outline btn-sm"
                    type="button"
                    disabled={!taskForm.content_id || videoUploading}
                    onClick={() => videoInputRef.current?.click()}
                  >
                    {videoUploading ? '上传中…' : '上传视频'}
                  </button>
                </div>
                {!taskForm.content_id ? (
                  <p className="admin-card-note">请先填写内容 ID，再上传或查看已绑定的视频素材。</p>
                ) : hasVideo ? (
                  <ul className="admin-video-list">
                    {contentVideos.map((v) => (
                      <li key={v.id}>
                        <span className="admin-video-name">{v.filename}</span>
                        <span className="admin-video-meta">{v.size_mb ? `${v.size_mb}MB` : ''}</span>
                        {v.url && (
                          <a className="admin-video-link" href={`${API_BASE}${v.url}`} target="_blank" rel="noreferrer">查看</a>
                        )}
                        <button className="btn btn-outline btn-sm" type="button" onClick={() => deleteContentVideo(v)}>移除</button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="admin-card-note admin-video-warn">该内容尚未绑定视频素材，视频平台发布前请先上传一个视频文件（mp4/mov/webm，≤500MB）。</p>
                )}
              </div>
            )}
            <label>发布方式
              <select value={taskForm.publish_mode} onChange={(e) => setTaskForm({ ...taskForm, publish_mode: e.target.value })}>
                <option value="direct">立即发布</option>
                <option value="schedule">定时发布</option>
              </select>
            </label>
            {taskForm.publish_mode === 'schedule' && (
              <label>发布时间
                <input type="datetime-local" value={taskForm.scheduled_at} onChange={(e) => setTaskForm({ ...taskForm, scheduled_at: e.target.value })} />
              </label>
            )}
            <p className="admin-card-note">图文平台会自动带上内容封面与绑定的素材图；短视频平台使用上方绑定的视频素材。发布过程会截图留痕，可在任务「日志」中查看。</p>
            <div className="admin-form-actions">
              <button
                className="btn btn-primary"
                type="button"
                disabled={needVideo && !hasVideo}
                onClick={createTask}
              >
                {taskForm.publish_mode === 'schedule' ? '登记定时发布' : '创建并发布'}
              </button>
              <button className="btn btn-outline" type="button" onClick={() => setShowCreateTask(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {/* 日志弹窗 */}
      {showLogs && logsTaskId && (
        <div className="admin-modal-overlay" onClick={() => setShowLogs(false)}>
          <div className="admin-modal admin-modal-wide" onClick={(e) => e.stopPropagation()}>
            <h3>执行日志 — 任务 #{logsTaskId}</h3>
            {logs.length === 0 ? (
              <p className="admin-empty">暂无日志记录。</p>
            ) : (
              <div className="admin-log-list">
                {logs.map((log) => (
                  <div key={log.id} className={`admin-log-item admin-log-${log.level}`}>
                    <span className="admin-log-time">{log.created_at ? log.created_at.slice(0, 19) : '-'}</span>
                    <span className="admin-log-level">{log.level}</span>
                    <span className="admin-log-message">{log.message}</span>
                  </div>
                ))}
              </div>
            )}
            <h4 style={{ marginTop: '1rem' }}>截图留痕</h4>
            {artifacts.length === 0 ? (
              <p className="admin-empty">暂无截图。发布执行后会自动记录关键步骤截图。</p>
            ) : (
              <div className="admin-artifact-grid">
                {artifacts.map((art) => (
                  <a
                    key={art.id}
                    className="admin-artifact-item"
                    href={art.url ? `${API_BASE}${art.url}` : '#'}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {art.url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={`${API_BASE}${art.url}`} alt={art.note || art.filename} />
                    ) : (
                      <span>{art.filename}</span>
                    )}
                    <span className="admin-artifact-note">{art.note || art.artifact_type}</span>
                  </a>
                ))}
              </div>
            )}
            <div className="admin-form-actions">
              <button className="btn btn-outline" type="button" onClick={() => setShowLogs(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
