export function formatDate(isoString?: string | null): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return '—';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);
  return `${mins}m ${secs}s`;
}

export function calculateElapsedTime(createdIso?: string | null, completedIso?: string | null): string {
  if (!createdIso) return '—';
  const start = new Date(createdIso).getTime();
  const end = completedIso ? new Date(completedIso).getTime() : Date.now();
  const diffSec = Math.max(0, (end - start) / 1000);
  return formatDuration(diffSec);
}

export function truncateUrl(url: string, maxLength: number = 45): string {
  if (!url) return '';
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength - 3) + '...';
}

export function isValidHttpUrl(string: string): boolean {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}
