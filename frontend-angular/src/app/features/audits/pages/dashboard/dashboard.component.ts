import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuditService } from '../../../../core/services/audit.service';
import type { AuditJob } from '../../../../core/models/audit.model';
import { StatusBadgeComponent } from '../../../../shared/components/status-badge/status-badge.component';
import { LoadingSkeletonComponent } from '../../../../shared/components/loading-skeleton/loading-skeleton.component';
import { formatDate, truncateUrl } from '../../../../shared/utils/formatting.utils';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, StatusBadgeComponent, LoadingSkeletonComponent],
  template: `
    <div class="space-y-8">
      <!-- Hero Header Banner -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-6 rounded-2xl border border-gray-800">
        <div class="space-y-1">
          <h1 class="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Brand Guardian AI
          </h1>
          <p class="text-sm text-gray-400">
            Video Compliance Intelligence & Multimodal Audit Engine
          </p>
        </div>

        <a
          routerLink="/audits/new"
          class="flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 transition-all cursor-pointer text-sm shrink-0"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>+ New Video Audit</span>
        </a>
      </div>

      <!-- Summary KPI Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-2">
          <div class="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>Total Audits</span>
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
          </div>
          <div class="text-2xl font-bold text-white font-mono">{{ totalAudits() }}</div>
          <div class="text-[11px] text-gray-400">Enqueued & Historical Jobs</div>
        </div>

        <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-2">
          <div class="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>Processing</span>
            <svg class="w-4 h-4 text-amber-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="text-2xl font-bold text-amber-400 font-mono">{{ processingCount() }}</div>
          <div class="text-[11px] text-gray-400">Active Pipeline Workers</div>
        </div>

        <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-2">
          <div class="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>Completed</span>
            <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
          </div>
          <div class="text-2xl font-bold text-emerald-400 font-mono">{{ completedCount() }}</div>
          <div class="text-[11px] text-gray-400">Verified Compliance Audits</div>
        </div>

        <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-2">
          <div class="flex items-center justify-between text-gray-400 text-xs font-medium">
            <span>Issues Found</span>
            <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          </div>
          <div class="text-2xl font-bold text-rose-400 font-mono">{{ issuesCount() }}</div>
          <div class="text-[11px] text-gray-400">FTC Violations Flagged</div>
        </div>
      </div>

      <!-- Audit History Table -->
      <div id="history" class="glass-panel p-6 rounded-2xl border border-gray-800 space-y-5">
        <div class="flex items-center justify-between border-b border-gray-800 pb-4">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <svg class="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              <span>Recent Video Audits</span>
            </h2>
            <p class="text-xs text-gray-400 mt-0.5">
              Real-time audit jobs processed by the LangGraph async backend
            </p>
          </div>

          <button
            (click)="refresh()"
            class="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-slate-950 px-3 py-1.5 rounded-lg border border-gray-800 transition-colors cursor-pointer"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            <span>Refresh</span>
          </button>
        </div>

        @if (loading()) {
          <app-loading-skeleton [rows]="4"></app-loading-skeleton>
        } @else if (error()) {
          <div class="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
            {{ error() }}
          </div>
        } @else if (audits().length === 0) {
          <div class="text-center py-12 space-y-3">
            <svg class="w-10 h-10 text-gray-600 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <div class="text-sm font-semibold text-gray-300">No completed audits yet</div>
            <p class="text-xs text-gray-500 max-w-sm mx-auto">
              Start your first video audit to analyze compliance disclosures, visual OCR, and FTC rules.
            </p>
            <a
              routerLink="/audits/new"
              class="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-xs transition-colors cursor-pointer"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>Start First Audit</span>
            </a>
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-sans">
              <thead>
                <tr class="text-gray-400 border-b border-gray-800 uppercase tracking-wider text-[11px]">
                  <th class="pb-3 font-medium">Audit ID</th>
                  <th class="pb-3 font-medium">Video URL</th>
                  <th class="pb-3 font-medium">Status</th>
                  <th class="pb-3 font-medium">Stage</th>
                  <th class="pb-3 font-medium">Created At</th>
                  <th class="pb-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/60">
                @for (job of audits(); track job.audit_id) {
                  <tr
                    (click)="viewAudit(job.audit_id)"
                    class="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                  >
                    <td class="py-3 font-mono font-medium text-cyan-400">
                      {{ job.audit_id.substring(0, 8) }}...
                    </td>
                    <td class="py-3 text-gray-300 max-w-xs font-mono truncate">
                      {{ truncate(job.video_url, 35) }}
                    </td>
                    <td class="py-3">
                      <app-status-badge [status]="job.status" size="sm"></app-status-badge>
                    </td>
                    <td class="py-3 text-gray-400 font-mono text-[11px]">
                      {{ job.current_stage || '—' }}
                    </td>
                    <td class="py-3 text-gray-400 font-mono text-[11px]">
                      {{ formatCreatedDate(job.created_at) }}
                    </td>
                    <td class="py-3 text-right">
                      <a
                        [routerLink]="['/audits', job.audit_id]"
                        (click)="$event.stopPropagation()"
                        class="inline-flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        <span>View</span>
                        <svg class="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
                        </svg>
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </div>
  `
})
export class DashboardComponent implements OnInit {
  private auditService = inject(AuditService);
  private router = inject(Router);

  audits = signal<AuditJob[]>([]);
  loading = signal<boolean>(true);
  error = signal<string | null>(null);

  totalAudits = signal<number>(0);
  processingCount = signal<number>(0);
  completedCount = signal<number>(0);
  issuesCount = signal<number>(0);

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading.set(true);
    this.error.set(null);

    this.auditService.listAudits(20).subscribe({
      next: (jobs) => {
        this.audits.set(jobs);
        this.totalAudits.set(jobs.length);
        this.processingCount.set(
          jobs.filter(j => j.status === 'PROCESSING' || j.status === 'QUEUED' || j.status === 'VERIFYING').length
        );
        this.completedCount.set(jobs.filter(j => j.status === 'COMPLETED').length);
        this.issuesCount.set(
          jobs.reduce((acc, j) => acc + (j.result?.compliance_results?.length || 0), 0)
        );
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err.message || 'Failed to fetch audit history.');
        this.loading.set(false);
      }
    });
  }

  viewAudit(auditId: string): void {
    this.router.navigate(['/audits', auditId]);
  }

  truncate(url: string, len: number): string {
    return truncateUrl(url, len);
  }

  formatCreatedDate(iso?: string | null): string {
    return formatDate(iso);
  }
}
