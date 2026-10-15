import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { TimingMetrics } from '../../../../core/models/audit.model';
import { formatDuration } from '../../../../shared/utils/formatting.utils';

interface MetricRow {
  label: string;
  key: string;
  isTotal?: boolean;
}

@Component({
  selector: 'app-stage-latency',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (!hasMetrics) {
      <div class="glass-panel p-5 rounded-xl border border-gray-800">
        <h4 class="text-sm font-semibold text-white flex items-center gap-2 mb-3">
          <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>Processing Latency Breakdown</span>
        </h4>
        <p class="text-xs text-gray-400 italic">
          Timing metrics not available for this audit run.
        </p>
      </div>
    } @else {
      <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-4">
        <div class="flex items-center justify-between border-b border-gray-800 pb-3">
          <h4 class="text-sm font-semibold text-white flex items-center gap-2">
            <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            <span>Processing Performance & Stage Latencies</span>
          </h4>
          <span class="text-xs text-gray-400 font-mono">Seconds</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-sans">
            <thead>
              <tr class="text-gray-400 border-b border-gray-800/60 uppercase tracking-wider text-[11px]">
                <th class="pb-2 font-medium">Pipeline Stage</th>
                <th class="pb-2 font-medium text-right">Duration</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-800/40">
              @for (row of metricRows; track row.key) {
                <tr [ngClass]="row.isTotal ? 'font-semibold text-white bg-slate-950/40' : 'text-gray-300'">
                  <td class="py-2">{{ row.label }}</td>
                  <td class="py-2 text-right font-mono">
                    @if (hasValue(row.key)) {
                      <span [ngClass]="row.isTotal ? 'text-emerald-400' : 'text-gray-300'">
                        {{ getFormattedDuration(row.key) }}
                      </span>
                    } @else {
                      <span class="text-gray-500">—</span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    }
  `
})
export class StageLatencyComponent {
  @Input() timingMetrics?: TimingMetrics | null;

  metricRows: MetricRow[] = [
    { label: 'Video Ingestion & Download', key: 'video_download' },
    { label: 'Azure Video Indexing', key: 'video_indexing' },
    { label: 'OpenCV Frame Extraction', key: 'frame_extraction' },
    { label: 'Vision Analysis', key: 'vision_analysis' },
    { label: 'Audit Planner', key: 'audit_planner' },
    { label: 'Auditor Agent', key: 'auditor_agent' },
    { label: 'Evidence Verifier', key: 'verifier_agent' },
    { label: 'Total Worker Duration', key: 'total_worker_duration', isTotal: true },
  ];

  get hasMetrics(): boolean {
    return !!this.timingMetrics && Object.keys(this.timingMetrics).length > 0;
  }

  hasValue(key: string): boolean {
    if (!this.timingMetrics) return false;
    const val = (this.timingMetrics as any)[key];
    return val !== undefined && val !== null;
  }

  getFormattedDuration(key: string): string {
    if (!this.timingMetrics) return '—';
    const val = (this.timingMetrics as any)[key];
    return formatDuration(val);
  }
}
