import React, { useState, useEffect } from 'react';
import type { AdminUser, ActivityLog, LoginHistoryRecord } from '../../../types/admin';
import { adminApi } from '../../../services/adminApi';
import { 
  X, Mail, User, Shield, Clock, Globe, Building2, 
  ShieldCheck, Monitor, Loader2, Database
} from 'lucide-react';

interface Props { 
  user: AdminUser; 
  onClose: () => void; 
}

const ROLE_COLORS: Record<string, string> = { 
  super_admin: '#f59e0b', 
  admin: '#6366f1', 
  user: '#10b981' 
};

const STATUS_COLORS: Record<string, string> = { 
  active: '#10b981', 
  suspended: '#ef4444', 
  pending: '#f59e0b' 
};

export function ViewUserModal({ user, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<'profile' | 'activity' | 'logins'>('profile');
  const [loading, setLoading] = useState<boolean>(true);
  const [scanCount, setScanCount] = useState<number>(0);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [loginHistory, setLoginHistory] = useState<LoginHistoryRecord[]>([]);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        // Fetch domain checks count
        const scanRes = await adminApi.getScanRecords({ page: 1, page_size: 1, user_id: user.id });
        setScanCount(scanRes.total);

        // Fetch activity logs
        const actRes = await adminApi.getActivityLogs({ page: 1, page_size: 25, user_id: user.id });
        setActivityLogs(actRes.logs);

        // Fetch login history
        const logRes = await adminApi.getLoginHistory({ page: 1, page_size: 25, user_id: user.id });
        setLoginHistory(logRes.records);
      } catch (err) {
        console.error('Failed to load user intelligence profile details:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [user.id]);

  const tabButtonStyle = (tab: typeof activeTab): React.CSSProperties => ({
    padding: '10px 16px',
    background: activeTab === tab ? 'rgba(99,102,241,0.15)' : 'transparent',
    border: 'none',
    borderBottom: activeTab === tab ? '2px solid #6366f1' : '2px solid transparent',
    color: activeTab === tab ? '#e2e8f0' : '#475569',
    fontSize: 12,
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  });

  return (
    <div style={{ 
      position: 'fixed', inset: 0, 
      background: 'rgba(5, 7, 16, 0.85)', 
      backdropFilter: 'blur(10px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', 
      zIndex: 200, padding: 20 
    }}>
      <div className="glass-panel" style={{ 
        background: 'rgba(10, 14, 26, 0.96)', 
        border: '1px solid rgba(99, 102, 241, 0.2)', 
        borderRadius: 24, 
        padding: 0, 
        width: '100%', 
        maxWidth: 620, 
        height: '90vh',
        maxHeight: 780,
        display: 'flex', 
        flexDirection: 'column',
        boxShadow: '0 24px 64px rgba(0, 0, 0, 0.8), 0 0 40px rgba(99, 102, 241, 0.1)',
        overflow: 'hidden',
        animation: 'modal-enter 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)'
      }}>
        {/* Top Header Card */}
        <div style={{ 
          padding: '24px 28px', 
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(10,14,26,0) 80%)',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between' 
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ 
              width: 56, height: 56, borderRadius: 16, 
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', 
              display: 'flex', alignItems: 'center', justifyContent: 'center', 
              color: 'white', fontSize: 24, fontWeight: 800,
              boxShadow: '0 8px 20px rgba(99,102,241,0.3)',
              textShadow: '0 2px 4px rgba(0,0,0,0.2)'
            }}>
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={{ color: '#f1f5f9', fontSize: 18, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                {user.full_name}
              </h2>
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                <span style={{ 
                  padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700, 
                  color: ROLE_COLORS[user.role] ?? '#64748b', 
                  background: `${ROLE_COLORS[user.role] ?? '#64748b'}15`,
                  border: `1px solid ${ROLE_COLORS[user.role] ?? '#64748b'}25`
                }}>
                  {user.role.replace('_', ' ').toUpperCase()}
                </span>
                <span style={{ 
                  padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700, 
                  color: STATUS_COLORS[user.status] ?? '#64748b', 
                  background: `${STATUS_COLORS[user.status] ?? '#64748b'}15`,
                  border: `1px solid ${STATUS_COLORS[user.status] ?? '#64748b'}25`
                }}>
                  {user.status.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
          <button 
            onClick={onClose} 
            style={{ 
              background: 'rgba(255,255,255,0.03)', 
              border: '1px solid rgba(255,255,255,0.06)', 
              borderRadius: 10,
              cursor: 'pointer', 
              color: '#94a3b8', 
              padding: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#white'; e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Selection Row */}
        <div style={{ 
          display: 'flex', 
          borderBottom: '1px solid rgba(255,255,255,0.04)', 
          background: 'rgba(5, 7, 16, 0.2)',
          padding: '0 12px'
        }}>
          <button onClick={() => setActiveTab('profile')} style={tabButtonStyle('profile')}>Profile & Stats</button>
          <button onClick={() => setActiveTab('activity')} style={tabButtonStyle('activity')}>Activity Trail</button>
          <button onClick={() => setActiveTab('logins')} style={tabButtonStyle('logins')}>Login Sessions</button>
        </div>

        {/* Modal Scrollable Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: '#475569' }}>
              <Loader2 size={36} className="animate-spin text-violet-500" />
              <span style={{ fontSize: 13, fontWeight: 500 }}>Fetching User Audit Intelligence...</span>
            </div>
          ) : (
            <div style={{ height: '100%' }}>
              {/* Tab 1: Profile & Stats */}
              {activeTab === 'profile' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20, animation: 'tab-fade-in 0.3s ease' }}>
                  
                  {/* Grid of Key Info Widgets */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    {/* Stat Card: Domains Checked */}
                    <div style={{ 
                      background: 'rgba(99,102,241,0.04)', 
                      border: '1px solid rgba(99,102,241,0.15)', 
                      borderRadius: 16, 
                      padding: 16,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 14
                    }}>
                      <div style={{ 
                        width: 42, height: 42, borderRadius: 10,
                        background: 'rgba(99,102,241,0.12)',
                        border: '1px solid rgba(99,102,241,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: '#8b5cf6'
                      }}>
                        <Database size={20} />
                      </div>
                      <div>
                        <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Checked Domains</span>
                        <span style={{ color: '#f1f5f9', fontSize: 20, fontWeight: 800, display: 'block', marginTop: 2 }}>{scanCount}</span>
                      </div>
                    </div>

                    {/* Stat Card: Status Check */}
                    <div style={{ 
                      background: 'rgba(16,185,129,0.04)', 
                      border: '1px solid rgba(16,185,129,0.15)', 
                      borderRadius: 16, 
                      padding: 16,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 14
                    }}>
                      <div style={{ 
                        width: 42, height: 42, borderRadius: 10,
                        background: 'rgba(16,185,129,0.12)',
                        border: '1px solid rgba(16,185,129,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: '#10b981'
                      }}>
                        <ShieldCheck size={20} />
                      </div>
                      <div>
                        <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Security Status</span>
                        <span style={{ color: user.status === 'active' ? '#34d399' : '#f87171', fontSize: 13, fontWeight: 800, display: 'block', marginTop: 4 }}>
                          {user.status === 'active' ? 'SECURED ACTIVE' : 'SUSPENDED'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* General Profile Row List */}
                  <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 18, padding: '8px 16px' }}>
                    <InfoField icon={<User size={14} />} label="Username / ID" value={user.username} />
                    <InfoField icon={<Mail size={14} />} label="Email Address" value={user.email} />
                    <InfoField icon={<Building2 size={14} />} label="Department" value={user.department || 'Unassigned'} />
                    <InfoField icon={<Clock size={14} />} label="Registered Date" value={new Date(user.created_at).toLocaleString()} />
                    <InfoField icon={<Clock size={14} />} label="Last Access Time" value={user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never logged in'} />
                    <InfoField icon={<Shield size={14} />} label="Failed Attempts" value={`${user.failed_login_count} tries`} />
                  </div>

                  {/* 30-Day Data Retention Banner */}
                  <div style={{ 
                    padding: '12px 16px', 
                    borderRadius: 14, 
                    background: 'rgba(99,102,241,0.05)', 
                    border: '1px solid rgba(99,102,241,0.15)',
                    fontSize: 11,
                    color: '#94a3b8',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    lineHeight: 1.5
                  }}>
                    <Globe size={16} style={{ color: '#8b5cf6', marginTop: 1, flexShrink: 0 }} />
                    <div>
                      <strong style={{ color: '#a78bfa' }}>30-Day Audit Data Retention Policy:</strong> To optimize system telemetry, activity trails, scanned domains and login session history records automatically refresh and prune after 30 days.
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Activity Trail */}
              {activeTab === 'activity' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16, animation: 'tab-fade-in 0.3s ease' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Admin Actions Log</span>
                    <span style={{ fontSize: 11, color: '#8b5cf6', fontWeight: 600 }}>Showing last 25 audits</span>
                  </div>

                  {activityLogs.length === 0 ? (
                    <div style={{ padding: '40px 20px', textAlign: 'center', border: '1px dashed rgba(255,255,255,0.06)', borderRadius: 16, color: '#475569', fontSize: 13 }}>
                      No documented activity actions.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {activityLogs.map((log) => (
                        <div key={log.id} style={{ 
                          background: 'rgba(255,255,255,0.02)', 
                          border: '1px solid rgba(255,255,255,0.04)', 
                          borderRadius: 14, 
                          padding: '12px 16px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 6
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                            <span style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 700, fontFamily: 'monospace' }}>
                              {log.action.replace('_', ' ')}
                            </span>
                            <span style={{ 
                              padding: '2px 8px', borderRadius: 5, fontSize: 9, fontWeight: 800, 
                              color: log.status === 'success' ? '#34d399' : '#f87171', 
                              background: log.status === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                              border: `1px solid ${log.status === 'success' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`
                            }}>
                              {log.status.toUpperCase()}
                            </span>
                          </div>

                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 10, color: '#475569' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                              <Globe size={10} />
                              <span>IP: <strong style={{ color: '#94a3b8' }}>{log.ip_address || '—'}</strong></span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                              <Monitor size={10} />
                              <span>Browser: <strong style={{ color: '#94a3b8' }}>{log.browser || '—'}</strong></span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                              <Clock size={10} />
                              <span>{new Date(log.created_at).toLocaleString()}</span>
                            </div>
                          </div>

                          {log.object_label && (
                            <div style={{ fontSize: 11, color: '#8b5cf6', background: 'rgba(139,92,246,0.05)', padding: '4px 10px', borderRadius: 6, display: 'inline-flex', alignSelf: 'flex-start', border: '1px solid rgba(139,92,246,0.1)' }}>
                              Target: {log.object_label} ({log.object_type || 'Object'})
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Login Sessions */}
              {activeTab === 'logins' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16, animation: 'tab-fade-in 0.3s ease' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Session Logs</span>
                    <span style={{ fontSize: 11, color: '#8b5cf6', fontWeight: 600 }}>Showing last 25 logins</span>
                  </div>

                  {loginHistory.length === 0 ? (
                    <div style={{ padding: '40px 20px', textAlign: 'center', border: '1px dashed rgba(255,255,255,0.06)', borderRadius: 16, color: '#475569', fontSize: 13 }}>
                      No documented login attempts.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {loginHistory.map((lh) => (
                        <div key={lh.id} style={{ 
                          background: 'rgba(255,255,255,0.02)', 
                          border: '1px solid rgba(255,255,255,0.04)', 
                          borderRadius: 14, 
                          padding: '12px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: 12
                        }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 700 }}>
                                {lh.ip_address || 'Unknown IP'}
                              </span>
                              <span style={{ fontSize: 10, color: '#64748b' }}>
                                ({lh.country || 'Unknown Loc'})
                              </span>
                            </div>
                            <span style={{ fontSize: 10, color: '#475569' }}>
                              {lh.browser || 'Unknown Browser'} on {lh.os || 'Unknown OS'}
                            </span>
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                            <span style={{ 
                              padding: '2px 8px', borderRadius: 5, fontSize: 9, fontWeight: 800, 
                              color: lh.success ? '#34d399' : '#f87171', 
                              background: lh.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                              border: `1px solid ${lh.success ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`
                            }}>
                              {lh.success ? 'SUCCESS' : 'FAILED'}
                            </span>
                            <span style={{ fontSize: 9, color: '#475569' }}>
                              {new Date(lh.login_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div style={{ 
          padding: '20px 28px', 
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          background: 'rgba(5, 7, 16, 0.4)',
          display: 'flex', 
          justifyContent: 'flex-end'
        }}>
          <button 
            onClick={onClose} 
            style={{ 
              padding: '10px 24px', 
              borderRadius: 10, 
              border: '1px solid rgba(255,255,255,0.08)', 
              background: 'transparent', 
              color: '#94a3b8', 
              cursor: 'pointer', 
              fontSize: 13,
              fontWeight: 600,
              transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#white'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}
          >
            Done
          </button>
        </div>
      </div>

      <style>{`
        @keyframes modal-enter {
          0% { opacity: 0; transform: translateY(40px) scale(0.96); filter: blur(6px); }
          100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
        }
        @keyframes tab-fade-in {
          0% { opacity: 0; transform: translateY(10px); }
          100% { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

function InfoField({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string | number | null }) {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between', 
      padding: '12px 0', 
      borderBottom: '1px solid rgba(255,255,255,0.04)',
      gap: 12
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ color: '#475569', display: 'flex', alignItems: 'center' }}>{icon}</div>
        <span style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      </div>
      <span style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 600, textAlign: 'right' }}>{value ?? '—'}</span>
    </div>
  );
}
