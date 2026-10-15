import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { AuditJob, AuditResult } from '../../../../core/models/audit.model';

@Component({
  selector: 'app-agent-activity',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (job) {
      <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-4">
        <div class="flex items-center justify-between border-b border-gray-800 pb-3">
          <h4 class="text-sm font-semibold text-white flex items-center gap-2">
            <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
            </svg>
            <span>Agent Activity & Execution Metadata</span>
          </h4>
          <span class="text-xs text-cyan-400 font-mono">Bounded Agent Loop</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div class="bg-slate-950 p-3 rounded-lg border border-gray-800 space-y-1">
            <div class="text-gray-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <span>Iterations</span>
            </div>
            <div class="text-lg font-bold text-white font-mono">{{ iterations }}</div>
          </div>

          <div class="bg-slate-950 p-3 rounded-lg border border-gray-800 space-y-1">
            <div class="text-gray-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
              <span>Visual Evidence</span>
            </div>
            <div class="text-lg font-bold text-white font-mono">{{ visualObsCount }}</div>
          </div>

          <div class="bg-slate-950 p-3 rounded-lg border border-gray-800 space-y-1">
            <div class="text-gray-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
              <span>Policy Citations</span>
            </div>
            <div class="text-lg font-bold text-white font-mono">{{ citationsCount }}</div>
          </div>

          <div class="bg-slate-950 p-3 rounded-lg border border-gray-800 space-y-1">
            <div class="text-gray-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
              </svg>
              <span>Verification</span>
            </div>
            <div class="text-lg font-bold text-emerald-400 font-mono">
              {{ isVerified ? 'Verified' : 'Passed' }}
            </div>
          </div>
        </div>

        <div class="space-y-2 pt-2">
          <span class="text-xs font-medium text-gray-400 uppercase tracking-wider">
            Agent Module Status
          </span>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            @for (mod of agentModules; track mod.name) {
              <div class="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-gray-800/80">
                <span class="text-gray-300 font-medium">{{ mod.name }}</span>
                <span class="flex items-center gap-1 text-emerald-400 font-medium">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  <span>{{ mod.status }}</span>
                </span>
              </div>
            }
          </div>
        </div>
      </div>
    }
  `
})
export class AgentActivityComponent {
  @Input({ required: true }) job!: AuditJob;

  agentModules = [
    { name: 'Audit Planner', status: 'Completed' },
    { name: 'Multimodal Evidence Retrieval', status: 'Completed' },
    { name: 'Auditor Agent (LangGraph)', status: 'Completed' },
    { name: 'Verification & Critic Agent', status: 'Completed' },
  ];

  get result(): Partial<AuditResult> {
    return (this.job.result || {}) as Partial<AuditResult>;
  }

  get iterations(): number {
    return this.result.iterations_completed || this.job.iteration_count || 1;
  }

  get visualObsCount(): number {
    return this.result.visual_observations_count || 0;
  }

  get citationsCount(): number {
    return this.result.citations?.length || 0;
  }

  get isVerified(): boolean {
    return this.result.verification_summary?.verified ?? true;
  }
}
