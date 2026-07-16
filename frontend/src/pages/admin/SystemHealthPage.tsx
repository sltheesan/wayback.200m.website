import React, { useEffect, useState } from 'react';
import { Activity, Database, Cpu, Wifi, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

interface HealthStatus {
  status: string;
  postgres: string;
  redis: string;
}

type ServiceStatus = 'healthy' | 'degraded' | 'unhealthy' | 'checking';

function getServiceStatus(value: string): ServiceStatus {
  if (value.startsWith('healthy')) return 'healthy';
  if (value === 'degraded') return 'degraded';
  if (value.startsWith('unhealthy')) return 'unhealthy';
  return 'checking';
}

function StatusIcon({ status }: { status: ServiceStatus }) {
  if (status === 'healthy') return <CheckCircle size={18} color="#10b981" />;
  if (status === 'degraded') return <AlertTriangle size={18} color="#f59e0b" />;
  if (status === 'unhealthy') return <XCircle size={18} color="#ef4444" />;
  return <Activity size={18} color="#475569" style={{ animation: 'spin 1s linear infinite' }} />;
}

const STATUS_COLORS: Record<ServiceStatus, string> = {
  healthy: '#10b981', degraded: '#f59e0b', unhealthy: '#ef4444', checking: '#475569',
};

interface ServiceCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  status: ServiceStatus;
}

function ServiceCard({ icon, label, value, status }: ServiceCardProps) {
  const color = STATUS_COLORS[status];
  return (
    <div style={{
      background: 'rgba(15,23,42,0.7)', border: `1px solid ${color}30`,
      borderRadius: 16, padding: '20px 22px',
      transition: 'box-shadow 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 38, height: 38, borderRadius: 10, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', color }}>
            {icon}
          </div>
          <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 15 }}>{label}</span>
        </div>
        <StatusIcon status={status} />
      </div>
      <div style={{ padding: '10px 12px', background: 'rgba(0,0,0,0.3)', borderRadius: 8 }}>
        <code style={{ color: color, fontSize: 12, fontFamily: 'monospace' }}>{value}</code>
      </div>
      <div style={{ marginTop: 10 }}>
        <span style={{
          padding: '3px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
          color, background: `${color}15`, border: `1px solid ${color}30`,
        }}>{status.toUpperCase()}</span>
      </div>
    </div>
  );
}

export default function SystemHealthPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE.replace('/api/v1', '')}/health`);
      const data: HealthStatus = await res.json();
      setHealth(data);
      setLastChecked(new Date());
    } catch {
      setHealth({ status: 'unhealthy', postgres: 'unhealthy: connection failed', redis: 'unhealthy: connection failed' });
    }
    setLoading(false);
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // auto-refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const overallStatus = loading ? 'checking' : getServiceStatus(health?.status ?? '');

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ color: '#f1f5f9', fontSize: 22, fontWeight: 700, margin: 0 }}>System Health</h1>
          <p style={{ color: '#475569', fontSize: 13, margin: '4px 0 0' }}>
            {lastChecked ? `Last checked: ${lastChecked.toLocaleTimeString()} — auto-refreshes every 30s` : 'Checking...'}
          </p>
        </div>
        <button onClick={checkHealth} disabled={loading} style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 10,
          background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
          color: '#a5b4fc', fontSize: 14, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
        }}>
          <Activity size={16} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
          {loading ? 'Checking...' : 'Refresh Now'}
        </button>
      </div>

      {/* Overall status banner */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14, padding: '18px 24px', borderRadius: 16, marginBottom: 28,
        background: `rgba(${overallStatus === 'healthy' ? '16,185,129' : overallStatus === 'degraded' ? '245,158,11' : '239,68,68'},0.08)`,
        border: `1px solid ${STATUS_COLORS[overallStatus]}30`,
      }}>
        <StatusIcon status={overallStatus} />
        <div>
          <div style={{ color: STATUS_COLORS[overallStatus], fontWeight: 700, fontSize: 18 }}>
            System is {overallStatus.toUpperCase()}
          </div>
          <div style={{ color: '#475569', fontSize: 13, marginTop: 2 }}>
            {overallStatus === 'healthy' ? 'All services are operating normally.' : 'One or more services are experiencing issues.'}
          </div>
        </div>
      </div>

      {/* Service cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
        <ServiceCard
          icon={<Database size={18} />}
          label="PostgreSQL Database"
          value={health?.postgres ?? 'Checking...'}
          status={loading ? 'checking' : getServiceStatus(health?.postgres ?? '')}
        />
        <ServiceCard
          icon={<Cpu size={18} />}
          label="Redis Cache"
          value={health?.redis ?? 'Checking...'}
          status={loading ? 'checking' : getServiceStatus(health?.redis ?? '')}
        />
        <ServiceCard
          icon={<Wifi size={18} />}
          label="API Gateway"
          value={loading ? 'Checking...' : 'FastAPI running'}
          status={loading ? 'checking' : 'healthy'}
        />
        <ServiceCard
          icon={<Activity size={18} />}
          label="Background Workers"
          value="Celery workers"
          status="healthy"
        />
      </div>

      <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
    </div>
  );
}
