import React from 'react';
import type { AdminUser } from '../../../types/admin';
import { X, Mail, User, Shield, Clock, Globe, Building2 } from 'lucide-react';

interface Props { user: AdminUser; onClose: () => void; }

const ROLE_COLORS: Record<string, string> = { super_admin: '#f59e0b', admin: '#6366f1', user: '#10b981' };
const STATUS_COLORS: Record<string, string> = { active: '#10b981', suspended: '#ef4444', pending: '#f59e0b' };

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string | number | null }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <div style={{ color: '#475569', marginTop: 1 }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ color: '#475569', fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 2 }}>{label}</div>
        <div style={{ color: '#e2e8f0', fontSize: 14 }}>{value ?? '—'}</div>
      </div>
    </div>
  );
}

export function ViewUserModal({ user, onClose }: Props) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200, padding: 20 }}>
      <div style={{ background: 'rgba(10,14,26,0.98)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 20, padding: 32, width: '100%', maxWidth: 480, maxHeight: '90vh', overflowY: 'auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 52, height: 52, borderRadius: 14, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 22, fontWeight: 700 }}>
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={{ color: '#f1f5f9', fontSize: 18, fontWeight: 700, margin: 0 }}>{user.full_name}</h2>
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, color: ROLE_COLORS[user.role] ?? '#64748b', background: `${ROLE_COLORS[user.role] ?? '#64748b'}20` }}>
                  {user.role.replace('_', ' ').toUpperCase()}
                </span>
                <span style={{ padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, color: STATUS_COLORS[user.status] ?? '#64748b', background: `${STATUS_COLORS[user.status] ?? '#64748b'}20` }}>
                  {user.status.toUpperCase()}
                </span>
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#475569', padding: 4 }}><X size={20} /></button>
        </div>

        {/* Info rows */}
        <InfoRow icon={<User size={14} />} label="Username" value={user.username} />
        <InfoRow icon={<Mail size={14} />} label="Email" value={user.email} />
        <InfoRow icon={<Building2 size={14} />} label="Department" value={user.department} />
        <InfoRow icon={<Clock size={14} />} label="Created At" value={new Date(user.created_at).toLocaleString()} />
        <InfoRow icon={<Clock size={14} />} label="Last Login" value={user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'} />
        <InfoRow icon={<Shield size={14} />} label="Failed Login Attempts" value={user.failed_login_count} />
        {user.locked_until && (
          <InfoRow icon={<Shield size={14} />} label="Locked Until" value={new Date(user.locked_until).toLocaleString()} />
        )}
        <InfoRow icon={<Globe size={14} />} label="User ID" value={`#${user.id}`} />

        {user.must_change_password && (
          <div style={{ marginTop: 16, padding: '10px 14px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 10, color: '#f59e0b', fontSize: 13 }}>
            ⚠️ This user must change their password on next login.
          </div>
        )}

        <button onClick={onClose} style={{ width: '100%', marginTop: 20, padding: '11px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 14 }}>
          Close
        </button>
      </div>
    </div>
  );
}
