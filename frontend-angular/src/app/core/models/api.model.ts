import type { AuditStatusType } from './audit.model';

export interface CreateAuditRequest {
  video_url: string;
}

export interface CreateAuditResponse {
  audit_id: string;
  status: AuditStatusType;
  video_url: string;
  message: string;
}

export interface AuditStatusResponse {
  audit_id: string;
  status: AuditStatusType;
  progress: number;
  current_stage: string;
  error_code?: string | null;
  error_message?: string | null;
}

export interface AuditReportResponse {
  audit_id: string;
  status: AuditStatusType;
  final_report: string;
}

export interface CancelAuditResponse {
  audit_id: string;
  status: AuditStatusType;
  message: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
}

export interface ReadinessStatus {
  status: 'ready' | 'unready';
  database: 'ok' | 'unavailable';
  redis: 'ok' | 'unavailable' | 'memory_fallback_active';
  redis_required: boolean;
  environment: Record<string, boolean>;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}
