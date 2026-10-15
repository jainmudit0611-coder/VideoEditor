import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuditService } from '../../../../core/services/audit.service';
import type { AuditJob } from '../../../../core/models/audit.model';
import { StatusBadgeComponent } from '../../../../shared/components/status-badge/status-badge.component';
import { WorkflowProgressComponent } from '../../components/workflow-progress/workflow-progress.component';
import { ReportViewerComponent } from '../../components/report-viewer/report-viewer.component';
import { LoadingSkeletonComponent } from '../../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ErrorAlertComponent } from '../../../../shared/components/error-alert/error-alert.component';

@Component({
  selector: 'app-audit-details',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    StatusBadgeComponent,
    WorkflowProgressComponent,
    ReportViewerComponent,
    LoadingSkeletonComponent,
    ErrorAlertComponent
  ],
  template: `
    <div class="space-y-6">
      @if (loading() && !job()) {
        <div class="space-y-6">
          <a
            routerLink="/dashboard"
            class="inline-flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-white transition-colors"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            <span>Back to Dashboard</span>
          </a>
          <app-loading-skeleton [rows]="5"></app-loading-skeleton>
        </div>
      } @else if (error() || !job()) {
        <div class="space-y-6">
          <a
            routerLink="/dashboard"
            class="inline-flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-white transition-colors cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            <span>Back to Dashboard</span>
          </a>
          <app-error-alert
            title="Audit Job Not Found"
            [message]="error() || 'No audit job found matching ID ' + auditId"
            [showRetry]="true"
            (retry)="startPolling()"
          ></app-error-alert>
        </div>
      } @else {
        <!-- Top Actions Bar -->
        <div class="flex items-center justify-between no-print">
          <a
            routerLink="/dashboard"
            class="inline-flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-white transition-colors cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
            </svg>
            <span>Back to Dashboard</span>
          </a>

          <div class="flex items-center gap-3">
            <button
              (click)="manualRefresh()"
              class="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-slate-950 px-3 py-1.5 rounded-lg border border-gray-800 transition-colors cursor-pointer"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <span>Refresh Status</span>
            </button>

            @if (canCancel) {
              <button
                (click)="onCancel()"
                [disabled]="cancelling()"
                class="flex items-center gap-1.5 text-xs text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 px-3 py-1.5 rounded-lg border border-rose-500/30 transition-colors cursor-pointer"
              >
                @if (cancelling()) {
                  <svg class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                } @else {
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                }
                <span>Cancel Audit</span>
              </button>
            }
          </div>
        </div>

        @if (cancelError()) {
          <app-error-alert title="Cancellation Error" [message]="cancelError()!"></app-error-alert>
        }

        <!-- Header Metadata Panel -->
        <div class="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800 pb-4">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                <h1 class="text-lg sm:text-xl font-bold text-white">Video Compliance Audit</h1>
              </div>
              <div class="flex items-center gap-2 text-xs text-gray-400 font-mono">
                <span>Audit ID: {{ job()!.audit_id }}</span>
              </div>
            </div>

            <app-status-badge [status]="job()!.status" size="lg"></app-status-badge>
          </div>

          <div class="flex items-center gap-2 text-xs font-mono text-cyan-400 bg-slate-950 p-3 rounded-xl border border-gray-800 break-all">
            <svg class="w-4 h-4 text-cyan-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
            <a
              [href]="job()!.video_url"
              target="_blank"
              rel="noopener noreferrer"
              class="hover:underline hover:text-cyan-300"
            >
              {{ job()!.video_url }}
            </a>
          </div>
        </div>

        <!-- Workflow Progress Timeline -->
        <app-workflow-progress [job]="job()!"></app-workflow-progress>

        <!-- Failed Audit View -->
        @if (job()!.status === 'FAILED') {
          <div class="glass-panel p-6 rounded-2xl border border-rose-500/30 bg-rose-500/5 space-y-4">
            <div class="flex items-start gap-3">
              <svg class="w-6 h-6 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <div class="space-y-2 text-xs text-rose-200">
                <h3 class="text-base font-bold text-rose-300">Audit Job Failed</h3>
                <p>
                  <strong>Error Code:</strong>
                  <span class="font-mono bg-rose-950 px-2 py-0.5 rounded border border-rose-800 ml-1">
                    {{ job()!.error_code || 'WORKFLOW_EXECUTION_ERROR' }}
                  </span>
                </p>
                <p class="font-mono leading-relaxed bg-slate-950 p-3 rounded-lg border border-gray-800 text-rose-200/90">
                  {{ job()!.error_message || 'An unhandled exception occurred during background processing.' }}
                </p>
                @if (job()!.retry_count > 0) {
                  <p class="text-gray-400">
                    Automatic retry attempts made: {{ job()!.retry_count }}
                  </p>
                }
              </div>
            </div>
          </div>
        }

        <!-- Cancelled Audit View -->
        @if (job()!.status === 'CANCELLED') {
          <div class="glass-panel p-6 rounded-2xl border border-slate-700 bg-slate-950/40 text-gray-400 text-xs text-center py-8">
            This video compliance audit was cancelled prior to completion.
          </div>
        }

        <!-- Completed Deliverables Report -->
        @if (job()!.status === 'COMPLETED') {
          <app-report-viewer [job]="job()!"></app-report-viewer>
        }
      }
    </div>
  `
})
export class AuditDetailsComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private auditService = inject(AuditService);

  auditId = '';
  job = signal<AuditJob | null>(null);
  loading = signal<boolean>(true);
  error = signal<string | null>(null);
  cancelling = signal<boolean>(false);
  cancelError = signal<string | null>(null);

  private pollSub?: Subscription;

  get canCancel(): boolean {
    const currentJob = this.job();
    return !!currentJob && (currentJob.status === 'QUEUED' || currentJob.status === 'PROCESSING' || currentJob.status === 'VERIFYING');
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.auditId = params.get('id') || '';
      if (this.auditId) {
        this.startPolling();
      } else {
        this.error.set('No audit ID specified');
        this.loading.set(false);
      }
    });
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  startPolling(): void {
    this.stopPolling();
    this.loading.set(true);
    this.error.set(null);

    this.pollSub = this.auditService.pollAudit(this.auditId).subscribe({
      next: (data) => {
        this.job.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err.message || 'Failed to fetch audit status.');
        this.loading.set(false);
      }
    });
  }

  stopPolling(): void {
    if (this.pollSub) {
      this.pollSub.unsubscribe();
      this.pollSub = undefined;
    }
  }

  manualRefresh(): void {
    this.auditService.getAudit(this.auditId).subscribe({
      next: (data) => this.job.set(data),
      error: (err) => this.error.set(err.message || 'Failed to refresh status.')
    });
  }

  onCancel(): void {
    const currentJob = this.job();
    if (!currentJob) return;

    if (!window.confirm('Are you sure you want to cancel this in-progress audit job?')) {
      return;
    }

    this.cancelling.set(true);
    this.cancelError.set(null);

    this.auditService.cancelAudit(currentJob.audit_id).subscribe({
      next: () => {
        this.cancelling.set(false);
        this.manualRefresh();
      },
      error: (err) => {
        this.cancelling.set(false);
        this.cancelError.set(err.message || 'Failed to cancel audit.');
      }
    });
  }
}
