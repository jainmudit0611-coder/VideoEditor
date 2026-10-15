import { Injectable, inject } from '@angular/core';
import { Observable, timer, of } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { ApiService } from './api.service';
import type { HealthStatus, ReadinessStatus } from '../models/api.model';

@Injectable({
  providedIn: 'root'
})
export class HealthService {
  private api = inject(ApiService);

  getHealth(): Observable<HealthStatus> {
    return this.api.get<HealthStatus>('/health');
  }

  getReadiness(): Observable<ReadinessStatus> {
    return this.api.get<ReadinessStatus>('/health/ready').pipe(
      catchError(() => of({
        status: 'unready',
        database: 'unavailable',
        redis: 'unavailable',
        redis_required: false,
        environment: {}
      } as ReadinessStatus))
    );
  }

  pollReadiness(intervalMs: number = 15000): Observable<ReadinessStatus> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getReadiness())
    );
  }
}
