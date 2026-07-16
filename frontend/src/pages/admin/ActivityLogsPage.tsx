import React, { useEffect, useState, useCallback } from 'react';
import { adminApi } from '../../services/adminApi';
import type { ActivityLogList } from '../../types/admin';
import { Download, Search, Shield } from 'lucide-react';

export default function ActivityLogsPage() {
  const [data, setData] = useState<ActivityLogList | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [page, setPage] = useState(1);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getActivityLogs({ page, page_size: 20, action: actionFilter || undefined });
      setData(res);
    } catch { /* ignore */ }
    setLoading(false);
  }, [page, actionFilter]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const inputStyle: React.CSSProperties = {
    background: 'rgba(30,41,59,0.6)', border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 10, color: '#e2e8f0', fontSize: 14, padding: '9px 14px', outline: 'none',
  };

  const ACTION_COLORS: Record<string, string> = {
    CREATE: '#10b981', DELETE: '#ef4444', UPDATE: '#6366f1',
    SUSPEND: '#f59e0b', ACTIVATE: '#10b981', RESET: '#8b5cf6',
    LOGIN: '#06b6d4', LOGOUT: '#475569',
  };

  const getActionColor = (action: string) => {
    for (const [key, color] of Object.entries(ACTION_COLORS)) {
      if (action.toUpperCase().includes(key)) return color;
    }
    return '#64748b';
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: 24 }}>
        <div>
          <h1 style={{ color: '#f1f5f9', fontSize: 22, fontWeight: 700, margin: 0 }}>Activity Logs</h1>
          <p style={{ color: '#475569', fontSize: 13, margin: '4px 0 0' }}>
            Immutable audit trail — {data?.total ?? 0} records. Nothing is deletable.
          </p>
        </div>
        <button onClick={() => adminApi.exportCSV('activity_logs')} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: 10, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#a5b4fc', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
          <Download size={15} /> Export CSV
        </button>
      </div>

      {/* Info banner */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 12, padding: '12px 16px', marginBottom: 20 }}>
        <Shield size={16} color="#6366f1" />
        <span style={{ color: '#94a3b8', fontSize: 13 }}>All admin actions are recorded here and cannot be deleted. This log is your enterprise-grade audit trail.</span>
      </div>

      {/* Filter */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <div style={{ position: 'relative', flex: '1 1 240px' }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#475569' }} />
          <input style={{ ...inputStyle, paddingLeft: 34, width: '100%', boxSizing: 'border-box' }} placeholder="Filter by action (e.g. CREATE, DELETE)..." value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); setPage(1); }} />
        </div>
      </div>

      {/* Table */}
      <div style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                {['Time', 'User', 'Role', 'Action', 'Object', 'IP', 'Browser', 'Status'].map((h) => (
                  <th key={h} style={{ padding: '13px 16px', textAlign: 'left', color: '#475569', fontWeight: 600, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: '#475569' }}>Loading...</td></tr>
              ) : !data?.logs.length ? (
                <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: '#475569' }}>No activity logs found.</td></tr>
              ) : data.logs.map((log) => {
                const color = getActionColor(log.action);
                return (
                  <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(99,102,241,0.04)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '12px 16px', color: '#475569', whiteSpace: 'nowrap', fontSize: 12 }}>{new Date(log.created_at).toLocaleString()}</td>
                    <td style={{ padding: '12px 16px', color: '#e2e8f0', fontWeight: 500 }}>{log.username_snapshot ?? '—'}</td>
                    <td style={{ padding: '12px 16px', color: '#64748b', fontSize: 12 }}>{log.user_role_snapshot ?? '—'}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, color, background: `${color}18`, whiteSpace: 'nowrap' }}>{log.action}</span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{log.object_label ?? log.object_id ?? '—'}</td>
                    <td style={{ padding: '12px 16px', color: '#475569', fontFamily: 'monospace', fontSize: 12 }}>{log.ip_address ?? '—'}</td>
                    <td style={{ padding: '12px 16px', color: '#475569' }}>{log.browser ?? '—'}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ color: log.status === 'success' ? '#10b981' : '#ef4444', fontSize: 12, fontWeight: 600 }}>{log.status}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {data && data.total_pages > 1 && (
          <div style={{ padding: '14px 16px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: '#475569', fontSize: 13 }}>Page {data.page} of {data.total_pages} ({data.total} total)</span>
            <div style={{ display: 'flex', gap: 8 }}>
              {Array.from({ length: Math.min(data.total_pages, 7) }, (_, i) => i + 1).map((p) => (
                <button key={p} onClick={() => setPage(p)} style={{ width: 32, height: 32, borderRadius: 8, fontSize: 13, background: p === page ? 'rgba(99,102,241,0.25)' : 'rgba(30,41,59,0.6)', border: p === page ? '1px solid rgba(99,102,241,0.4)' : '1px solid rgba(255,255,255,0.06)', color: p === page ? '#a5b4fc' : '#475569', cursor: 'pointer' }}>{p}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
