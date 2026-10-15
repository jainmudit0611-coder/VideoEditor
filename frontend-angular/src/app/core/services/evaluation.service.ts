import { Injectable, inject } from '@angular/core';
import { Observable, timer } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { ApiService } from './api.service';
import type {
  EvaluationRun,
  EvaluationRunStatus,
  CreateEvaluationRunRequest,
  CreateEvaluationRunResponse,
  EvaluationComparison,
} from '../models/evaluation.model';

const TERMINAL_STATUSES = ['COMPLETED', 'FAILED'];

@Injectable({
  providedIn: 'root'
})
export class EvaluationService {
  private api = inject(ApiService);

  createRun(request: CreateEvaluationRunRequest = {}): Observable<CreateEvaluationRunResponse> {
    return this.api.post<CreateEvaluationRunResponse>('/api/evaluations/runs', request);
  }

  listRuns(params?: { dataset_version?: string; status?: string; model_name?: string }): Observable<EvaluationRun[]> {
    let url = '/api/evaluations/runs';
    if (params) {
      const q = new URLSearchParams();
      if (params.dataset_version) q.set('dataset_version', params.dataset_version);
      if (params.status) q.set('status', params.status);
      if (params.model_name) q.set('model_name', params.model_name);
      const queryStr = q.toString();
      if (queryStr) url += `?${queryStr}`;
    }
    return this.api.get<EvaluationRun[]>(url);
  }

  getRun(runId: string): Observable<EvaluationRun> {
    return this.api.get<EvaluationRun>(`/api/evaluations/runs/${runId}`);
  }

  getRunStatus(runId: string): Observable<EvaluationRunStatus> {
    return this.api.get<EvaluationRunStatus>(`/api/evaluations/runs/${runId}/status`);
  }

  compareRuns(runIds: string[]): Observable<EvaluationComparison> {
    const idsParam = encodeURIComponent(runIds.join(','));
    return this.api.get<EvaluationComparison>(`/api/evaluations/compare?run_ids=${idsParam}`);
  }

  /**
   * Polls an active evaluation run every intervalMs (default 2s) until COMPLETED or FAILED.
   * Emits the complete EvaluationRun state on each poll.
   */
  pollRun(runId: string, intervalMs: number = 2000): Observable<EvaluationRun> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getRun(runId)),
      takeWhile(run => !TERMINAL_STATUSES.includes(run.status), true)
    );
  }
}
