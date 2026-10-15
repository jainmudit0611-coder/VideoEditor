import { Injectable, inject } from '@angular/core';
import { HttpHeaders } from '@angular/common/http';
import { Observable, timer } from 'rxjs';
import { switchMap, takeWhile, distinctUntilChanged } from 'rxjs/operators';
import { ApiService } from './api.service';
import type {
  CreateAuditRequest,
  CreateAuditResponse,
  AuditStatusResponse,
  AuditReportResponse,
  CancelAuditResponse,
} from '../models/api.model';
import type { AuditJob, AuditStatusType } from '../models/audit.model';

const TERMINAL_STATUSES: AuditStatusType[] = ['COMPLETED', 'FAILED', 'CANCELLED'];

@Injectable({
  providedIn: 'root'
})
export class AuditService {
  private api = inject(ApiService);

  createAudit(videoUrl: string, idempotencyKey?: string): Observable<CreateAuditResponse> {
    let headers: HttpHeaders | undefined;
    if (idempotencyKey) {
      headers = new HttpHeaders({ 'Idempotency-Key': idempotencyKey });
    }
    return this.api.post<CreateAuditResponse>('/audits', { video_url: videoUrl } as CreateAuditRequest, headers);
  }

  listAudits(limit: number = 20, offset: number = 0): Observable<AuditJob[]> {
    return this.api.get<AuditJob[]>(`/audits?limit=${limit}&offset=${offset}`);
  }

  getAudit(auditId: string): Observable<AuditJob> {
    return this.api.get<AuditJob>(`/audits/${auditId}`);
  }

  getAuditStatus(auditId: string): Observable<AuditStatusResponse> {
    return this.api.get<AuditStatusResponse>(`/audits/${auditId}/status`);
  }

  getAuditReport(auditId: string): Observable<AuditReportResponse> {
    return this.api.get<AuditReportResponse>(`/audits/${auditId}/report`);
  }

  cancelAudit(auditId: string): Observable<CancelAuditResponse> {
    return this.api.post<CancelAuditResponse>(`/audits/${auditId}/cancel`, {});
  }

  /**
   * Polls an audit job every 2.5 seconds using RxJS until terminal status reached.
   * Emits the full AuditJob object on each poll.
   */
  pollAudit(auditId: string, intervalMs: number = 2500): Observable<AuditJob> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getAudit(auditId)),
      // Take while not in terminal status, inclusive of the final terminal emission
      takeWhile(job => !TERMINAL_STATUSES.includes(job.status), true)
    );
  }
}
