import type { AuditStatusType } from '../../core/models/audit.model';

export function getStatusColorClass(status: AuditStatusType | string): {
  badge: string;
  dot: string;
  border: string;
} {
  switch (status) {
    case 'COMPLETED':
      return {
        badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        dot: 'bg-emerald-400',
        border: 'border-emerald-500/40',
      };
    case 'PROCESSING':
    case 'VERIFYING':
      return {
        badge: 'bg-blue-500/10 text-blue-400 border-blue-500/30 animate-pulse',
        dot: 'bg-blue-400 animate-ping',
        border: 'border-blue-500/40',
      };
    case 'QUEUED':
      return {
        badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        dot: 'bg-amber-400',
        border: 'border-amber-500/40',
      };
    case 'FAILED':
      return {
        badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
        dot: 'bg-rose-400',
        border: 'border-rose-500/40',
      };
    case 'CANCELLED':
      return {
        badge: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
        dot: 'bg-slate-400',
        border: 'border-slate-500/40',
      };
    default:
      return {
        badge: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
        dot: 'bg-slate-400',
        border: 'border-slate-500/40',
      };
  }
}

export function getSeverityColorClass(severity: string): {
  badge: string;
  icon: string;
} {
  const upper = (severity || '').toUpperCase();
  if (upper === 'PASS' || upper === 'SUCCESS' || upper === 'LOW') {
    return {
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      icon: 'text-emerald-400',
    };
  }
  if (upper === 'WARNING' || upper === 'MEDIUM' || upper === 'AMBER') {
    return {
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      icon: 'text-amber-400',
    };
  }
  if (upper === 'FAIL' || upper === 'HIGH' || upper === 'CRITICAL' || upper === 'ERROR') {
    return {
      badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      icon: 'text-rose-400',
    };
  }
  return {
    badge: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
    icon: 'text-slate-400',
  };
}

export function formatStageTitle(stage: string): string {
  if (!stage) return 'Queued';
  return stage
    .toLowerCase()
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
