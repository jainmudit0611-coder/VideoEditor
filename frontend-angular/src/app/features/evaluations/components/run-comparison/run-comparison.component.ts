import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { EvaluationComparison } from '../../../../core/models/evaluation.model';

@Component({
  selector: 'app-run-comparison',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (visible && comparison) {
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
        <div class="relative w-full max-w-5xl bg-slate-900 border border-gray-800 rounded-xl shadow-2xl p-6 sm:p-8 my-8 max-h-[90vh] overflow-y-auto">
          <!-- Header -->
          <div class="flex items-center justify-between pb-6 border-b border-gray-800">
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Run Comparison
                </span>
                <span class="text-xs text-gray-400">Comparing {{ comparison.runs.length }} Historical Runs</span>
              </div>
              <h2 class="text-xl sm:text-2xl font-bold text-white mt-1">Evaluation Run Comparison</h2>
              <p class="text-xs text-gray-400 mt-0.5">
                Descriptive comparison of metrics and pipeline configuration. Values are reported neutrally without assigning winners.
              </p>
            </div>
            <button
              (click)="close.emit()"
              class="p-2 text-gray-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              aria-label="Close Comparison"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Compared Runs Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6">
            @for (run of comparison.runs; track run.id; let idx = $index) {
              <div class="bg-slate-950 p-4 rounded-lg border border-gray-800">
                <div class="flex items-center justify-between text-xs text-gray-400 mb-1">
                  <span class="font-semibold text-blue-400 uppercase tracking-wider">Run {{ idx === 0 ? 'A' : 'B' }}</span>
                  <span class="font-mono text-[11px]">{{ run.id | slice:0:8 }}</span>
                </div>
                <h3 class="text-base font-bold text-white truncate">{{ run.run_name }}</h3>
                <div class="mt-2 text-xs text-gray-300 space-y-1">
                  <div class="flex justify-between">
                    <span class="text-gray-400">Model:</span>
                    <span class="font-mono text-gray-200">{{ run.model_name }} ({{ run.model_provider }})</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-400">Prompt / Config:</span>
                    <span class="font-mono text-gray-200">{{ run.prompt_version }} / {{ run.config_version }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-400">Dataset:</span>
                    <span class="font-mono text-gray-200">{{ run.dataset_version }} (N={{ run.case_count }})</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-400">Duration:</span>
                    <span class="font-mono text-gray-200">{{ run.duration_ms ? (run.duration_ms / 1000).toFixed(2) + 's' : '—' }}</span>
                  </div>
                </div>
              </div>
            }
          </div>

          <!-- Metrics Comparison Table -->
          <div class="mt-6">
            <h3 class="text-sm font-semibold text-gray-200 mb-3 uppercase tracking-wider">Metrics Comparison</h3>
            <div class="overflow-x-auto rounded-lg border border-gray-800">
              <table class="w-full text-left text-xs">
                <thead class="bg-slate-950/80 text-gray-400 border-b border-gray-800 uppercase text-[11px] tracking-wider">
                  <tr>
                    <th class="p-3">Evaluation Metric</th>
                    @for (run of comparison.runs; track run.id; let idx = $index) {
                      <th class="p-3 text-right">Run {{ idx === 0 ? 'A' : 'B' }}</th>
                    }
                    @if (comparison.runs.length === 2) {
                      <th class="p-3 text-right font-mono">Difference (Δ)</th>
                    }
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-800/60 font-mono">
                  @for (row of comparison.metrics; track row.key) {
                    <tr class="hover:bg-slate-800/40 transition-colors">
                      <td class="p-3 font-sans font-medium text-gray-200">{{ row.metric }}</td>
                      @for (run of comparison.runs; track run.id) {
                        <td class="p-3 text-right text-gray-300">
                          {{ formatMetricValue(row.values[run.id], row.display_type) }}
                        </td>
                      }
                      @if (comparison.runs.length === 2) {
                        <td class="p-3 text-right font-semibold" [ngClass]="getDeltaClass(row.delta)">
                          {{ formatDelta(row.delta, row.display_type) }}
                        </td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Metadata Differences -->
          <div class="mt-8">
            <h3 class="text-sm font-semibold text-gray-200 mb-3 uppercase tracking-wider">Configuration & Metadata Differences</h3>
            <div class="overflow-x-auto rounded-lg border border-gray-800">
              <table class="w-full text-left text-xs font-mono">
                <thead class="bg-slate-950/80 text-gray-400 border-b border-gray-800 uppercase text-[11px] tracking-wider font-sans">
                  <tr>
                    <th class="p-3">Configuration Parameter</th>
                    @for (run of comparison.runs; track run.id; let idx = $index) {
                      <th class="p-3 text-right">Run {{ idx === 0 ? 'A' : 'B' }}</th>
                    }
                    <th class="p-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-800/60 font-mono">
                  @for (diff of comparison.differences; track diff.field) {
                    <tr class="hover:bg-slate-800/40 transition-colors">
                      <td class="p-3 font-sans font-medium text-gray-300">{{ diff.field }}</td>
                      @for (run of comparison.runs; track run.id) {
                        <td class="p-3 text-right text-gray-300">
                          {{ diff.values[run.id] ?? '—' }}
                        </td>
                      }
                      <td class="p-3 text-center">
                        @if (diff.has_difference) {
                          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            Different
                          </span>
                        } @else {
                          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20">
                            Identical
                          </span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Close Footer -->
          <div class="mt-8 pt-4 border-t border-gray-800 flex justify-end">
            <button
              (click)="close.emit()"
              class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-gray-200 text-sm font-medium rounded-lg transition-colors"
            >
              Close Comparison
            </button>
          </div>
        </div>
      </div>
    }
  `
})
export class RunComparisonComponent {
  @Input() comparison: EvaluationComparison | null = null;
  @Input() visible: boolean = false;
  @Output() close = new EventEmitter<void>();

  formatMetricValue(val: any, displayType: string): string {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val !== 'number') return String(val);
    if (displayType === '%') {
      return (val * 100).toFixed(1) + '%';
    }
    return val.toFixed(2);
  }

  formatDelta(delta: number | null | undefined, displayType: string): string {
    if (delta === null || delta === undefined) return '—';
    const sign = delta > 0 ? '+' : '';
    if (displayType === '%') {
      return sign + (delta * 100).toFixed(1) + '%';
    }
    return sign + delta.toFixed(2);
  }

  getDeltaClass(delta: number | null | undefined): string {
    if (delta === null || delta === undefined || delta === 0) return 'text-gray-400';
    return delta > 0 ? 'text-blue-400' : 'text-amber-400';
  }
}
