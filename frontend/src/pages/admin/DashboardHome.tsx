import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { adminApi } from '../../services/adminApi';
import type { DashboardStats } from '../../types/admin';
import {
  Users, ShieldAlert, Globe, TrendingUp,
  UserCheck, UserX, Activity,
} from 'lucide-react';

const CARD_STYLES = (accent: string) => ({
  background: 'rgba(15,23,42,0.7)',
  border: `1px solid ${accent}30`,
  borderRadius: 16, padding: '20px 22px',
  backdropFilter: 'blur(12px)',
  transition: 'transform 0.2s, box-shadow 0.2s',
  cursor: 'default',
});

interface StatCardProps {
  label: string; value: number | string;
  icon: React.ReactNode; accent: string; sub?: string;
}
function StatCard({ label, value, icon, accent, sub }: StatCardProps) {
  return (
    <div style={CARD_STYLES(accent)}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
        (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 30px ${accent}20`;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
        (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ color: '#64748b', fontSize: 12, fontWeight: 500, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
          <div style={{ color: '#f1f5f9', fontSize: 32, fontWeight: 700, lineHeight: 1 }}>{value.toLocaleString()}</div>
          {sub && <div style={{ color: '#475569', fontSize: 12, marginTop: 6 }}>{sub}</div>}
        </div>
        <div style={{
          width: 44, height: 44, borderRadius: 12,
          background: `${accent}18`, color: accent,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {icon}
        </div>
      </div>
    </div>
  );
}

const PIE_COLORS = { SAFE: '#10b981', MEDIUM: '#f59e0b', HIGH: '#ef4444' };
const CHART_TOOLTIP_STYLE = {
  background: 'rgba(10,14,26,0.95)',
  border: '1px solid rgba(99,102,241,0.3)',
  borderRadius: 10, color: '#e2e8f0',
};

export default function DashboardHome() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    adminApi.getDashboardStats()
      .then(setStats)
      .catch(() => setError('Failed to load dashboard stats.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: '#64748b' }}>
      <Activity size={24} style={{ animation: 'spin 1s linear infinite', marginRight: 10 }} />
      Loading dashboard...
    </div>
  );

  if (error) return <div style={{ color: '#ef4444', padding: 24 }}>{error}</div>;
  if (!stats) return null;

  const pieData = Object.entries(stats.safe_vs_unsafe).map(([name, value]) => ({ name, value }));

  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ color: '#f1f5f9', fontSize: 24, fontWeight: 700, margin: 0 }}>Dashboard Overview</h1>
        <p style={{ color: '#475569', fontSize: 14, margin: '6px 0 0' }}>
          Real-time statistics across users, scans, and system health.
        </p>
      </div>

      {/* Stat Cards — Row 1: Users */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
        <StatCard label="Total Users" value={stats.total_users} icon={<Users size={20} />} accent="#6366f1" />
        <StatCard label="Total Admins" value={stats.total_admins} icon={<ShieldAlert size={20} />} accent="#8b5cf6" />
        <StatCard label="Active Users" value={stats.active_users} icon={<UserCheck size={20} />} accent="#10b981" />
        <StatCard label="Suspended" value={stats.suspended_users} icon={<UserX size={20} />} accent="#ef4444" />
      </div>

      {/* Stat Cards — Row 2: Scans */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
        <StatCard label="Total Domains Checked" value={stats.total_domains_checked} icon={<Globe size={20} />} accent="#06b6d4" />
        <StatCard label="Today's Checks" value={stats.todays_checks} icon={<TrendingUp size={20} />} accent="#6366f1" />
        <StatCard label="Unsafe Domains" value={stats.unsafe_domains} icon={<ShieldAlert size={20} />} accent="#ef4444" sub="HIGH + MEDIUM risk" />
        <StatCard label="Safe Domains" value={stats.safe_domains} icon={<Globe size={20} />} accent="#10b981" />
      </div>

      {/* Charts Row 1 */}
      <div className="dashboard-charts-grid-2-1">
        {/* Checks per day */}
        <div style={{ ...CARD_STYLES('#6366f1'), padding: '20px' }}>
          <h3 style={{ color: '#e2e8f0', fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>Domain Checks per Day</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={stats.checks_per_day}>
              <defs>
                <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: '#475569', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Area type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} fill="url(#grad1)" name="Checks" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Safe vs Unsafe */}
        <div style={{ ...CARD_STYLES('#10b981'), padding: '20px' }}>
          <h3 style={{ color: '#e2e8f0', fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
                dataKey="value" nameKey="name" paddingAngle={4}
              >
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={PIE_COLORS[entry.name as keyof typeof PIE_COLORS] ?? '#64748b'} />
                ))}
              </Pie>
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Legend formatter={(v: string) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="dashboard-charts-grid-1-1">
        {/* Most Checked Domains */}
        <div style={{ ...CARD_STYLES('#06b6d4'), padding: '20px' }}>
          <h3 style={{ color: '#e2e8f0', fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>Most Checked Domains</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.most_checked_domains} layout="vertical">
              <XAxis type="number" tick={{ fill: '#475569', fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis dataKey="domain" type="category" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} width={100} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#06b6d4" radius={[0, 4, 4, 0]} name="Checks" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* User Activity (logins) */}
        <div style={{ ...CARD_STYLES('#8b5cf6'), padding: '20px' }}>
          <h3 style={{ color: '#e2e8f0', fontSize: 15, fontWeight: 600, margin: '0 0 16px' }}>User Logins per Day</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={stats.users_activity}>
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: '#475569', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="logins" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Logins" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <style>{`
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        .dashboard-charts-grid-2-1 {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 20px;
          margin-bottom: 20px;
        }
        .dashboard-charts-grid-1-1 {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        @media (max-width: 992px) {
          .dashboard-charts-grid-2-1,
          .dashboard-charts-grid-1-1 {
            grid-template-columns: 1fr !important;
            gap: 16px !important;
          }
        }
      `}</style>
    </div>
  );
}
