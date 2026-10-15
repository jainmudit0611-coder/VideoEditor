import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { ComplianceIssue } from '../../../../core/models/audit.model';
import { getSeverityColorClass } from '../../../../shared/utils/status.utils';

@Component({
  selector: 'app-findings-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (!findings || findings.length === 0) {
      <div class="glass-panel p-6 rounded-xl border border-gray-800 text-center space-y-2">
        <svg class="w-8 h-8 text-emerald-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
        <h4 class="text-sm font-semibold text-white">No Compliance Violations Detected</h4>
        <p class="text-xs text-gray-400">
          The video content passed all configured FTC, brand safety, and disclosure rules.
        </p>
      </div>
    } @else {
      <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-4">
        <div class="flex items-center justify-between border-b border-gray-800 pb-3">
          <h3 class="text-base font-semibold text-white flex items-center gap-2">
            <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <span>Compliance Findings ({{ findings.length }})</span>
          </h3>
          <span class="text-xs text-gray-400">FTC & Brand Safety Violations</span>
        </div>

        <div class="space-y-3">
          @for (issue of findings; track $index) {
            <div class="p-4 rounded-xl bg-slate-950/80 border border-gray-800 space-y-2 hover:border-gray-700 transition-colors">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  @if (isFail(issue.severity)) {
                    <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  } @else if (isPass(issue.severity)) {
                    <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                    </svg>
                  } @else {
                    <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                    </svg>
                  }
                  <span class="text-sm font-semibold text-white">
                    {{ issue.category || 'Compliance Finding' }}
                  </span>
                </div>

                <div class="flex items-center gap-2">
                  @if (issue.timestamp) {
                    <span class="flex items-center gap-1 text-[11px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                      <span>{{ issue.timestamp }}</span>
                    </span>
                  }

                  <span
                    class="px-2.5 py-0.5 rounded-full text-xs font-semibold border"
                    [ngClass]="getSeverityClass(issue.severity).badge"
                  >
                    {{ (issue.severity || 'WARNING').toUpperCase() }}
                  </span>
                </div>
              </div>

              <p class="text-xs text-gray-300 leading-relaxed font-sans">
                {{ issue.description }}
              </p>

              @if (issue.rule_id) {
                <div class="flex items-center gap-1.5 text-[11px] text-gray-500 font-mono pt-1">
                  <svg class="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>
                  </svg>
                  <span>Rule ID: {{ issue.rule_id }}</span>
                </div>
              }
            </div>
          }
        </div>
      </div>
    }
  `
})
export class FindingsListComponent {
  @Input() findings?: ComplianceIssue[];

  getSeverityClass(severity: string) {
    return getSeverityColorClass(severity);
  }

  isFail(severity: string): boolean {
    const s = (severity || '').toUpperCase();
    return s === 'FAIL' || s === 'HIGH' || s === 'CRITICAL' || s === 'ERROR';
  }

  isPass(severity: string): boolean {
    const s = (severity || '').toUpperCase();
    return s === 'PASS' || s === 'SUCCESS' || s === 'LOW';
  }
}
