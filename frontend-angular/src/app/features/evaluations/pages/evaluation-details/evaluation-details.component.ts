import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { EvaluationService } from '../../../../core/services/evaluation.service';
import type { EvaluationRun } from '../../../../core/models/evaluation.model';

@Component({
  selector: 'app-evaluation-details',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <!-- Back Navigation & Actions -->
      <div class="flex items-center justify-between">
        <a
          routerLink="/evaluations"
          class="inline-flex items-center gap-2 text-sm font-semibold text-gray-400 hover:text-white transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          <span>Back to Evaluation Dashboard</span>
        </a>

        @if (run) {
          <div class="flex items-center gap-2">
            <span
              class="px-2.5 py-1 rounded text-xs font-semibold uppercase tracking-wider"
              [ngClass]="{
                'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20': run.status === 'COMPLETED',
                'bg-blue-500/10 text-blue-400 border border-blue-500/20': run.status === 'RUNNING' || run.status === 'QUEUED',
                'bg-rose-500/10 text-rose-400 border border-rose-500/20': run.status === 'FAILED'
              }"
            >
              {{ run.status }}
            </span>
          </div>
        }
      </div>

      @if (isLoading) {
        <div class="py-16 text-center text-gray-400 text-sm">
          <svg class="w-8 h-8 animate-spin mx-auto text-blue-400 mb-3" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading evaluation run details...
        </div>
      } @else if (!run) {
        <div class="bg-slate-900 border border-gray-800 rounded-xl p-8 text-center text-gray-400">
          Evaluation run not found or failed to load.
        </div>
      } @else {
        <!-- Main Run Header -->
        <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 sm:p-8 shadow-xl">
          <div class="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-gray-800 gap-4">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">Run Details</span>
                <span class="font-mono text-xs text-gray-400">#{{ run.id }}</span>
              </div>
              <h1 class="text-2xl sm:text-3xl font-bold text-white mt-1">{{ run.run_name }}</h1>
              <p class="text-xs text-gray-400 font-mono mt-1">
                Completed on {{ run.completed_at ? (run.completed_at | date:'medium') : '—' }} • Duration: {{ run.duration_ms ? (run.duration_ms / 1000).toFixed(2) + 's' : '—' }}
              </p>
            </div>
          </div>

          <!-- Metadata Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 text-xs">
            <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
              <span class="text-gray-400">Dataset</span>
              <p class="text-white font-mono font-semibold mt-1">{{ run.dataset_version }} ({{ run.dataset_type }})</p>
              <span class="text-[11px] text-gray-400">{{ run.case_count }} test cases</span>
            </div>

            <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
              <span class="text-gray-400">Model & Provider</span>
              <p class="text-white font-mono font-semibold mt-1">{{ run.model_name }}</p>
              <span class="text-[11px] text-gray-400">{{ run.model_provider }}</span>
            </div>

            <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
              <span class="text-gray-400">Prompt / Config</span>
              <p class="text-white font-mono font-semibold mt-1">{{ run.prompt_version }} / {{ run.config_version }}</p>
              <span class="text-[11px] text-gray-400">Evaluation v{{ run.evaluation_version }}</span>
            </div>

            <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
              <span class="text-gray-400">Execution Mode(s)</span>
              <p class="text-white font-mono font-semibold mt-1">
                {{ run.summary?.execution_modes?.join(', ') || 'NATIVE_VISION' }}
              </p>
              <span class="text-[11px] text-gray-400">Offline benchmark</span>
            </div>
          </div>
        </div>

        <!-- Metric Groups Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Finding Quality -->
          <div class="bg-slate-900 border border-gray-800 rounded-xl p-5 shadow-lg">
            <div class="flex items-center justify-between pb-3 border-b border-gray-800">
              <h3 class="text-sm font-semibold text-white uppercase tracking-wider">Finding Quality</h3>
              <span class="text-xs font-mono font-bold text-blue-400">F1: {{ run.metrics.finding_f1 !== undefined && run.metrics.finding_f1 !== null ? run.metrics.finding_f1.toFixed(2) : 'N/A' }}</span>
            </div>
            <div class="mt-4 space-y-3 text-xs">
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Precision:</span>
                <span class="font-mono font-bold text-white">{{ formatPercent(run.metrics.finding_precision) }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Recall:</span>
                <span class="font-mono font-bold text-white">{{ formatPercent(run.metrics.finding_recall) }}</span>
              </div>
              <div class="flex justify-between items-center text-gray-400 pt-2 border-t border-gray-800/60 font-mono">
                <span>TP / FP / FN:</span>
                <span class="text-gray-300">
                  {{ run.metrics.true_positives || 0 }} / {{ run.metrics.false_positives || 0 }} / {{ run.metrics.false_negatives || 0 }}
                </span>
              </div>
            </div>
          </div>

          <!-- Evidence Grounding -->
          <div class="bg-slate-900 border border-gray-800 rounded-xl p-5 shadow-lg">
            <div class="flex items-center justify-between pb-3 border-b border-gray-800">
              <h3 class="text-sm font-semibold text-white uppercase tracking-wider">Evidence Grounding</h3>
              <span class="text-xs font-mono font-bold text-emerald-400">{{ formatPercent(run.metrics.evidence_support_rate) }}</span>
            </div>
            <div class="mt-4 space-y-3 text-xs">
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Support Rate:</span>
                <span class="font-mono font-bold text-emerald-400">{{ formatPercent(run.metrics.evidence_support_rate) }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Unsupported Rate:</span>
                <span class="font-mono font-bold text-white">{{ formatPercent(run.metrics.unsupported_finding_rate) }}</span>
              </div>
              <div class="flex justify-between items-center text-gray-400 pt-2 border-t border-gray-800/60 font-mono">
                <span>Modality Checks:</span>
                <span class="text-gray-300">Transcript, OCR</span>
              </div>
            </div>
          </div>

          <!-- Citations & Verifier -->
          <div class="bg-slate-900 border border-gray-800 rounded-xl p-5 shadow-lg">
            <div class="flex items-center justify-between pb-3 border-b border-gray-800">
              <h3 class="text-sm font-semibold text-white uppercase tracking-wider">Citations & Verifier</h3>
              <span class="text-xs font-mono font-bold text-indigo-400">
                {{ run.metrics.verifier_agreement_rate !== null && run.metrics.verifier_agreement_rate !== undefined ? formatPercent(run.metrics.verifier_agreement_rate) : 'N/A' }}
              </span>
            </div>
            <div class="mt-4 space-y-3 text-xs">
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Citation Presence:</span>
                <span class="font-mono font-bold text-white">{{ formatPercent(run.metrics.citation_presence_rate) }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Citation Completeness:</span>
                <span class="font-mono font-bold text-white">{{ formatPercent(run.metrics.citation_completeness_rate) }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Schema Conformance:</span>
                <span class="font-mono font-bold text-white">{{ formatPercent(run.metrics.schema_validity_rate) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Latency Breakdown -->
        @if (run.metrics.latency; as lat) {
          <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 shadow-xl">
            <h3 class="text-sm font-semibold text-white uppercase tracking-wider mb-4">Pipeline Latency Performance</h3>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
                <span class="text-gray-400 font-sans">Mean Audit Duration</span>
                <p class="text-lg font-bold text-white mt-1">{{ lat.mean_duration_sec ?? '—' }}s</p>
              </div>
              <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
                <span class="text-gray-400 font-sans">Median Duration</span>
                <p class="text-lg font-bold text-white mt-1">{{ lat.median_duration_sec ?? '—' }}s</p>
              </div>
              <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
                <span class="text-gray-400 font-sans">Minimum Duration</span>
                <p class="text-lg font-bold text-white mt-1">{{ lat.min_duration_sec ?? '—' }}s</p>
              </div>
              <div class="bg-slate-950 p-3.5 rounded-lg border border-gray-800/80">
                <span class="text-gray-400 font-sans">Maximum Duration</span>
                <p class="text-lg font-bold text-white mt-1">{{ lat.max_duration_sec ?? '—' }}s</p>
              </div>
            </div>
          </div>
        }

        <!-- Case-by-Case Breakdown Table -->
        @if (run.summary?.case_results && run.summary!.case_results!.length > 0) {
          <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 shadow-xl">
            <h3 class="text-sm font-semibold text-white uppercase tracking-wider mb-4">Benchmark Case Breakdown (N={{ run.summary!.case_results!.length }})</h3>
            <div class="overflow-x-auto rounded-lg border border-gray-800">
              <table class="w-full text-left text-xs">
                <thead class="bg-slate-950/80 text-gray-400 border-b border-gray-800 uppercase text-[11px] tracking-wider">
                  <tr>
                    <th class="p-3">Case ID</th>
                    <th class="p-3">Execution Mode</th>
                    <th class="p-3 text-center">Expected / Actual</th>
                    <th class="p-3 text-center">TP / FP / FN</th>
                    <th class="p-3 text-right">Precision</th>
                    <th class="p-3 text-right">Recall</th>
                    <th class="p-3 text-right">Grounding %</th>
                    <th class="p-3 text-right">Citations %</th>
                    <th class="p-3 text-center">Verifier</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-800/60 font-mono">
                  @for (c of run.summary!.case_results; track c.case_id) {
                    <tr class="hover:bg-slate-800/30 transition-colors">
                      <td class="p-3 font-semibold text-blue-400">{{ c.case_id }}</td>
                      <td class="p-3 text-gray-300 font-mono text-[11px]">{{ c.execution_mode }}</td>
                      <td class="p-3 text-center text-gray-300">{{ c.findings_summary.expected }} / {{ c.findings_summary.actual }}</td>
                      <td class="p-3 text-center text-gray-300">{{ c.findings_summary.tp }} / {{ c.findings_summary.fp }} / {{ c.findings_summary.fn }}</td>
                      <td class="p-3 text-right text-gray-200">{{ formatPercent(c.findings_summary.precision) }}</td>
                      <td class="p-3 text-right text-gray-200">{{ formatPercent(c.findings_summary.recall) }}</td>
                      <td class="p-3 text-right text-emerald-400 font-semibold">{{ formatPercent(c.grounding.support_rate) }}</td>
                      <td class="p-3 text-right text-gray-200">{{ formatPercent(c.citation.presence_rate) }}</td>
                      <td class="p-3 text-center">
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-slate-950 text-gray-300 border border-gray-800">
                          {{ c.verifier.status }}
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        <!-- Discrepancies / Error Analysis Detail -->
        <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 shadow-xl">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-white uppercase tracking-wider">Detailed Error Analysis</h3>
            <span class="text-xs font-mono text-gray-400">{{ run.discrepancies?.length || 0 }} Discrepancies</span>
          </div>

          @if (!run.discrepancies || run.discrepancies.length === 0) {
            <p class="text-xs text-gray-400">
              No errors or discrepancies recorded in this evaluation run. All outputs conformed strictly to benchmark reference labels.
            </p>
          } @else {
            <div class="space-y-4">
              @for (disc of run.discrepancies; track disc.case_id + disc.failure_type; let idx = $index) {
                <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80 text-xs space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="font-semibold text-blue-400">#{{ idx + 1 }}: Case {{ disc.case_id }}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      {{ disc.failure_type }}
                    </span>
                  </div>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-gray-300">
                    <div><span class="text-gray-400">Expected:</span> {{ disc.expected || 'N/A' }}</div>
                    <div><span class="text-gray-400">Actual:</span> {{ disc.actual || 'N/A' }}</div>
                  </div>
                  <p class="text-gray-300 pt-1 border-t border-gray-800/60">
                    <strong class="text-gray-400">Observed Discrepancy:</strong> {{ disc.observed_discrepancy }}
                  </p>
                </div>
              }
            </div>
          }
        </div>
      }
    </div>
  `
})
export class EvaluationDetailsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private evalService = inject(EvaluationService);

  run: EvaluationRun | null = null;
  isLoading = false;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadRun(id);
    }
  }

  loadRun(id: string): void {
    this.isLoading = true;
    this.evalService.getRun(id).subscribe({
      next: (res) => {
        this.run = res;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load run details:', err);
        this.isLoading = false;
      }
    });
  }

  formatPercent(val?: number | null): string {
    if (val === null || val === undefined) return 'N/A';
    return (val * 100).toFixed(0) + '%';
  }
}
