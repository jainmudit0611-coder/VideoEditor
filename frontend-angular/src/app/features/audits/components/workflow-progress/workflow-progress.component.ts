import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { AuditJob } from '../../../../core/models/audit.model';
import { calculateElapsedTime } from '../../../../shared/utils/formatting.utils';

interface WorkflowStage {
  id: string;
  name: string;
  stages: string[];
}

const STAGES: WorkflowStage[] = [
  { id: 'ingestion', name: 'Video Ingestion', stages: ['QUEUED', 'DOWNLOADING'] },
  { id: 'extraction', name: 'Evidence Extraction', stages: ['VIDEO_INDEXING', 'FRAME_EXTRACTION'] },
  { id: 'planning', name: 'Audit Planning', stages: ['VISION_ANALYSIS', 'PLANNING'] },
  { id: 'auditing', name: 'Auditor Agent', stages: ['AUDITING'] },
  { id: 'verification', name: 'Evidence Verification', stages: ['VERIFYING'] },
  { id: 'report', name: 'Report Generation', stages: ['COMPLETED'] },
];

@Component({
  selector: 'app-workflow-progress',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (job) {
      <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
          <div>
            <h3 class="text-base font-semibold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
              </svg>
              <span>Agentic Workflow Execution Path</span>
            </h3>
            <p class="text-xs text-gray-400 mt-0.5">
              Real-time status tracking across LangGraph compliance stages
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-4 text-xs font-medium">
            <div class="bg-slate-950 px-3 py-1.5 rounded-lg border border-gray-800 flex items-center gap-2">
              <svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span class="text-gray-400">Elapsed:</span>
              <span class="font-mono text-gray-200">
                {{ elapsedTime }}
              </span>
            </div>

            <div class="bg-slate-950 px-3 py-1.5 rounded-lg border border-gray-800 flex items-center gap-2">
              <svg class="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <span class="text-gray-400">Iterations:</span>
              <span class="font-mono text-gray-200">{{ job.iteration_count || 1 }}</span>
            </div>

            @if (job.retry_count > 0) {
              <div class="bg-amber-500/10 px-3 py-1.5 rounded-lg border border-amber-500/30 text-amber-300 flex items-center gap-1.5">
                <span>Retries: {{ job.retry_count }}</span>
              </div>
            }
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs text-gray-400 font-medium">
            <span>Current Stage: <strong class="text-blue-400">{{ job.current_stage }}</strong></span>
            <span>{{ job.progress }}%</span>
          </div>
          <div class="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-gray-800">
            <div
              class="h-full transition-all duration-500 rounded-full"
              [ngClass]="progressBarColor"
              [style.width.%]="progressWidth"
            ></div>
          </div>
        </div>

        <!-- Interactive Timeline Stages -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          @for (stageObj of stages; track stageObj.id; let idx = $index) {
            <div
              class="p-3 rounded-lg border flex flex-col justify-between space-y-2 transition-all"
              [ngClass]="getStageClasses(stageObj, idx)"
            >
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono uppercase text-gray-400">
                  0{{ idx + 1 }}
                </span>
                @switch (getStageStatus(stageObj, idx)) {
                  @case ('completed') {
                    <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  }
                  @case ('active') {
                    <svg class="w-4 h-4 text-blue-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                  }
                  @case ('failed') {
                    <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  }
                  @default {
                    <div class="w-3.5 h-3.5 rounded-full border border-gray-700"></div>
                  }
                }
              </div>
              <span class="text-xs font-semibold leading-tight">{{ stageObj.name }}</span>
            </div>
          }
        </div>
      </div>
    }
  `
})
export class WorkflowProgressComponent {
  @Input({ required: true }) job!: AuditJob;
  stages = STAGES;

  private _cachedElapsedTime: string = '';
  private _lastJob: AuditJob | null = null;

  get elapsedTime(): string {
    if (!this.job) return '-';
    if (this.job.completed_at) {
      return calculateElapsedTime(this.job.created_at, this.job.completed_at);
    }
    if (this._lastJob !== this.job) {
      this._lastJob = this.job;
      this._cachedElapsedTime = calculateElapsedTime(this.job.created_at, this.job.completed_at);
    }
    return this._cachedElapsedTime;
  }

  get progressWidth(): number {
    return Math.max(this.job.progress || 0, 5);
  }

  get progressBarColor(): string {
    if (this.job.status === 'FAILED') return 'bg-rose-500';
    if (this.job.status === 'CANCELLED') return 'bg-slate-500';
    return 'bg-gradient-to-r from-blue-600 via-cyan-500 to-emerald-400';
  }

  getStageStatus(stageObj: WorkflowStage, index: number): 'completed' | 'active' | 'failed' | 'upcoming' {
    const currentStage = (this.job.current_stage || 'QUEUED').toUpperCase();
    const isFailed = this.job.status === 'FAILED';
    const isCancelled = this.job.status === 'CANCELLED';

    if (isFailed || isCancelled) {
      if (stageObj.stages.includes(currentStage)) {
        return 'failed';
      }
    }

    if (this.job.status === 'COMPLETED') {
      return 'completed';
    }

    const currentStageIndex = STAGES.findIndex((s) => s.stages.includes(currentStage));

    if (currentStageIndex === -1) {
      return index === 0 ? 'active' : 'upcoming';
    }

    if (index < currentStageIndex) {
      return 'completed';
    } else if (index === currentStageIndex) {
      return 'active';
    } else {
      return 'upcoming';
    }
  }

  getStageClasses(stageObj: WorkflowStage, index: number): string {
    const status = this.getStageStatus(stageObj, index);
    switch (status) {
      case 'completed':
        return 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300';
      case 'active':
        return 'bg-blue-500/10 border-blue-500/40 text-blue-300 shadow-md shadow-blue-500/5';
      case 'failed':
        return 'bg-rose-500/10 border-rose-500/40 text-rose-300';
      default:
        return 'bg-slate-950/40 border-gray-800/80 text-gray-500';
    }
  }
}
