export type EvaluationStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface EvaluationDiscrepancy {
  case_id: string;
  failure_type: 'FALSE_POSITIVE' | 'FALSE_NEGATIVE' | 'SEVERITY_MISMATCH' | 'UNSUPPORTED_FINDING' | 'SCHEMA_ERROR';
  expected?: string | null;
  actual?: string | null;
  evidence?: string | null;
  observed_discrepancy: string;
}

export interface CaseResultItem {
  case_id: string;
  execution_mode: string;
  findings_summary: {
    expected: number;
    actual: number;
    tp: number;
    fp: number;
    fn: number;
    precision: number;
    recall: number;
    f1: number;
  };
  grounding: {
    support_rate: number;
    supported: number;
    total: number;
  };
  citation: {
    presence_rate: number;
    completeness_rate: number;
  };
  schema: {
    is_valid: boolean;
    validity_rate: number;
  };
  verifier: {
    status: string;
    expected?: string | null;
    actual?: string | null;
  };
  timing?: Record<string, number>;
  discrepancy_count: number;
}

export interface EvaluationRunMetrics {
  finding_precision?: number;
  finding_recall?: number;
  finding_f1?: number;
  true_positives?: number;
  false_positives?: number;
  false_negatives?: number;
  total_expected_findings?: number;
  total_actual_findings?: number;
  evidence_support_rate?: number;
  unsupported_finding_rate?: number;
  citation_presence_rate?: number;
  citation_completeness_rate?: number;
  schema_validity_rate?: number;
  verifier_agreement_rate?: number | null;
  latency?: {
    n_samples?: number;
    mean_duration_sec?: number | null;
    median_duration_sec?: number | null;
    min_duration_sec?: number | null;
    max_duration_sec?: number | null;
    stage_latencies?: Record<string, number>;
  };
  mode_breakdown?: Record<string, {
    cases: number;
    precision: number;
    recall: number;
  }>;
}

export interface EvaluationRun {
  id: string;
  run_name: string;
  status: EvaluationStatus;
  dataset_version: string;
  dataset_type: string;
  case_count: number;
  model_name: string;
  model_provider: string;
  prompt_version: string;
  config_version: string;
  evaluation_version: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  created_at?: string | null;
  metrics: EvaluationRunMetrics;
  summary?: {
    dataset_version?: string;
    dataset_type?: string;
    cases_evaluated?: number;
    execution_modes?: string[];
    case_results?: CaseResultItem[];
    limitations?: string[];
  };
  discrepancies?: EvaluationDiscrepancy[];
  discrepancy_count?: number;
  error_message?: string | null;
}

export interface CreateEvaluationRunRequest {
  run_name?: string;
  model_name?: string;
  model_provider?: string;
  dataset_version?: string;
  prompt_version?: string;
  config_version?: string;
}

export interface CreateEvaluationRunResponse {
  id: string;
  run_name: string;
  status: EvaluationStatus;
  message: string;
}

export interface EvaluationRunStatus {
  id: string;
  run_name: string;
  status: EvaluationStatus;
  progress?: number | null;
  duration_ms?: number | null;
  case_count: number;
  error_message?: string | null;
}

export interface MetricComparisonRow {
  metric: string;
  key: string;
  display_type: string;
  values: Record<string, any>;
  delta?: number | null;
}

export interface MetadataDifferenceRow {
  field: string;
  values: Record<string, any>;
  has_difference: boolean;
}

export interface EvaluationComparison {
  runs: Array<{
    id: string;
    run_name: string;
    status: string;
    model_name: string;
    model_provider: string;
    prompt_version: string;
    config_version: string;
    dataset_version: string;
    dataset_type: string;
    case_count: number;
    duration_ms?: number | null;
    completed_at?: string | null;
  }>;
  metrics: MetricComparisonRow[];
  differences: MetadataDifferenceRow[];
}
