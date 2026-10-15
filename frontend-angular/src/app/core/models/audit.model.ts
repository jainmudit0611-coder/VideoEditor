export type AuditStatusType = 
  | 'QUEUED'
  | 'PROCESSING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type AuditStageType =
  | 'QUEUED'
  | 'DOWNLOADING'
  | 'VIDEO_INDEXING'
  | 'FRAME_EXTRACTION'
  | 'VISION_ANALYSIS'
  | 'PLANNING'
  | 'AUDITING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface ComplianceIssue {
  category: string;
  severity: 'PASS' | 'WARNING' | 'FAIL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  description: string;
  timestamp?: string | null;
  rule_id?: string;
}

export interface Citation {
  source?: string;
  policy_name?: string;
  rule_text?: string;
  relevance_score?: number;
  content?: string;
  [key: string]: any;
}

export interface VerificationSummary {
  status?: string;
  verified?: boolean;
  score?: number;
  reasoning?: string;
  claims_verified?: number;
  claims_flagged?: number;
  evidence_matched?: boolean;
  [key: string]: any;
}

export interface TimingMetrics {
  video_download?: number;
  video_indexing?: number;
  frame_extraction?: number;
  vision_analysis?: number;
  audit_planner?: number;
  auditor_agent?: number;
  verifier_agent?: number;
  total_worker_duration?: number;
  [key: string]: number | undefined;
}

export interface EvidenceItem {
  timestamp?: string;
  type: 'TRANSCRIPT' | 'OCR' | 'VISUAL' | string;
  content: string;
  confidence?: number;
  source?: string;
  frame_path?: string;
}

export interface AuditResult {
  audit_id: string;
  video_id: string;
  status: string;
  final_report: string;
  compliance_results: ComplianceIssue[];
  citations?: Citation[];
  verification_summary?: VerificationSummary;
  iterations_completed?: number;
  visual_observations_count?: number;
  is_degraded_vision_mode?: boolean;
  retrieved_evidence?: EvidenceItem[];
  transcript_items?: EvidenceItem[];
  ocr_items?: EvidenceItem[];
  visual_observations?: EvidenceItem[];
  [key: string]: any;
}

export interface AuditJob {
  audit_id: string;
  status: AuditStatusType;
  video_url: string;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  progress: number;
  current_stage: AuditStageType | string;
  iteration_count: number;
  retry_count: number;
  idempotency_key?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  error_details?: Record<string, any> | null;
  result?: AuditResult | null;
  timing_metrics?: TimingMetrics | null;
  created_by?: string | null;
}
