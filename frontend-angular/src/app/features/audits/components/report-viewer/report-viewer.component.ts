import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { AuditJob, AuditResult } from '../../../../core/models/audit.model';
import { DegradedModeBannerComponent } from '../../../../shared/components/degraded-mode-banner/degraded-mode-banner.component';
import { VerifierCardComponent } from '../verifier-card/verifier-card.component';
import { FindingsListComponent } from '../findings-list/findings-list.component';
import { EvidenceExplorerComponent } from '../evidence-explorer/evidence-explorer.component';
import { PolicyCitationsComponent } from '../policy-citations/policy-citations.component';
import { AgentActivityComponent } from '../agent-activity/agent-activity.component';
import { StageLatencyComponent } from '../stage-latency/stage-latency.component';

@Component({
  selector: 'app-report-viewer',
  standalone: true,
  imports: [
    CommonModule,
    DegradedModeBannerComponent,
    VerifierCardComponent,
    FindingsListComponent,
    EvidenceExplorerComponent,
    PolicyCitationsComponent,
    AgentActivityComponent,
    StageLatencyComponent
  ],
  template: `
    @if (job) {
      <div class="space-y-6">
        <!-- Header Actions -->
        <div class="flex items-center justify-between no-print">
          <div>
            <h2 class="text-xl font-bold text-white flex items-center gap-2">
              <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <span>Compliance Audit Report</span>
            </h2>
            <p class="text-xs text-gray-400">
              Generated deliverables and evidence verification summary
            </p>
          </div>

          <button
            (click)="printReport()"
            class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-md transition-colors cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
            </svg>
            <span>Print Report</span>
          </button>
        </div>

        <!-- Execution Mode Banner -->
        <app-degraded-mode-banner [isDegraded]="isDegraded"></app-degraded-mode-banner>

        <!-- Report Content Container -->
        <div class="space-y-6">
          <!-- Executive Summary Markdown Box -->
          <div class="glass-panel p-6 rounded-xl border border-gray-800 space-y-4">
            <h3 class="text-base font-semibold text-white border-b border-gray-800 pb-3">
              Executive Summary
            </h3>
            <div class="prose prose-invert max-w-none text-xs text-gray-200 leading-relaxed font-mono whitespace-pre-wrap bg-slate-950/70 p-4 rounded-lg border border-gray-800">
              {{ reportMarkdown }}
            </div>
          </div>

          <!-- Verifier Result -->
          <app-verifier-card [summary]="result.verification_summary"></app-verifier-card>

          <!-- Compliance Findings -->
          <app-findings-list [findings]="result.compliance_results"></app-findings-list>

          <!-- Evidence Explorer -->
          <app-evidence-explorer [result]="asAuditResult(result)" [isDegraded]="isDegraded"></app-evidence-explorer>

          <!-- Policy Citations -->
          <app-policy-citations [citations]="result.citations"></app-policy-citations>

          <!-- Agent Activity -->
          <app-agent-activity [job]="job"></app-agent-activity>

          <!-- Latency Metrics -->
          <app-stage-latency [timingMetrics]="job.timing_metrics"></app-stage-latency>
        </div>
      </div>
    }
  `
})
export class ReportViewerComponent {
  @Input({ required: true }) job!: AuditJob;

  get result(): Partial<AuditResult> {
    return (this.job.result || {}) as Partial<AuditResult>;
  }

  get reportMarkdown(): string {
    return this.result.final_report || 'No detailed markdown report available.';
  }

  get isDegraded(): boolean {
    return this.result.is_degraded_vision_mode || false;
  }

  asAuditResult(res: Partial<AuditResult>): AuditResult {
    return res as AuditResult;
  }

  printReport(): void {
    window.print();
  }
}
