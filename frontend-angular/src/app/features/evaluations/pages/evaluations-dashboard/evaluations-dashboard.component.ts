import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { EvaluationService } from '../../../../core/services/evaluation.service';
import { RunComparisonComponent } from '../../components/run-comparison/run-comparison.component';
import type {
  EvaluationRun,
  EvaluationComparison,
  EvaluationDiscrepancy,
} from '../../../../core/models/evaluation.model';

@Component({
  selector: 'app-evaluations-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, RunComparisonComponent],
  template: `
    <div class="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <!-- Title & Dataset Header Banner -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
              AI Quality & Evaluation
            </span>
            <span class="text-xs text-gray-400 font-mono">Dataset v1 • MANUALLY_CURATED • 6 cases</span>
          </div>
          <h1 class="text-2xl sm:text-3xl font-bold text-white tracking-tight mt-1">
            Compliance Evaluation Dashboard
          </h1>
          <p class="text-sm text-gray-400 mt-1 max-w-3xl">
            Independent deterministic evaluation framework measuring finding classification precision/recall, multimodal evidence grounding, policy citations, and schema quality.
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            (click)="triggerEvaluationRun()"
            [disabled]="isTriggering || isRunning"
            class="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            @if (isTriggering || isRunning) {
              <svg class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>{{ isTriggering ? 'Starting...' : 'Evaluating Benchmark...' }}</span>
            } @else {
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>Run Evaluation</span>
            }
          </button>
        </div>
      </div>

      <!-- Scientific Disclaimer Callout -->
      <div class="bg-slate-900/60 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3 text-xs text-amber-200/90">
        <svg class="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <div class="space-y-0.5">
          <p class="font-semibold text-amber-300">Methodology & Dataset Scope:</p>
          <p class="text-gray-300 leading-relaxed">
            Evaluation metrics are calculated against a manually curated reference benchmark of <strong>6 policy compliance cases</strong> (FTC disclosures, health substantiations, organic editorial controls). These results validate rule adherence and should not be interpreted as population-wide production accuracy.
          </p>
        </div>
      </div>

      <!-- Active In-Progress Banner -->
      @if (isRunning && activeRun) {
        <div class="bg-blue-950/40 border border-blue-500/40 rounded-xl p-4 flex items-center justify-between animate-pulse">
          <div class="flex items-center gap-3">
            <div class="w-3 h-3 bg-blue-400 rounded-full animate-ping"></div>
            <div>
              <p class="text-sm font-semibold text-white">Evaluation Run Active: {{ activeRun.run_name }}</p>
              <p class="text-xs text-blue-300/80 font-mono">Running benchmark suite across {{ activeRun.case_count }} test cases...</p>
            </div>
          </div>
          <span class="text-xs font-mono px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
            {{ activeRun.status }}
          </span>
        </div>
      }

      <!-- Latest Evaluation Run Overview Card -->
      @if (latestRun) {
        <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 shadow-xl">
          <div class="flex flex-col lg:flex-row lg:items-center justify-between pb-5 border-b border-gray-800 gap-4">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold uppercase tracking-wider text-gray-400">Latest Run</span>
                <span class="font-mono text-xs text-gray-500">#{{ latestRun.id | slice:0:8 }}</span>
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider"
                  [ngClass]="{
                    'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20': latestRun.status === 'COMPLETED',
                    'bg-blue-500/10 text-blue-400 border border-blue-500/20': latestRun.status === 'RUNNING' || latestRun.status === 'QUEUED',
                    'bg-rose-500/10 text-rose-400 border border-rose-500/20': latestRun.status === 'FAILED'
                  }"
                >
                  {{ latestRun.status }}
                </span>
              </div>
              <h2 class="text-xl font-bold text-white mt-1">{{ latestRun.run_name }}</h2>
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400 mt-1 font-mono">
                <span>Model: <strong class="text-gray-200">{{ latestRun.model_name }}</strong></span>
                <span>Provider: <strong class="text-gray-200">{{ latestRun.model_provider }}</strong></span>
                <span>Prompt/Config: <strong class="text-gray-200">{{ latestRun.prompt_version }} / {{ latestRun.config_version }}</strong></span>
                <span>Duration: <strong class="text-gray-200">{{ latestRun.duration_ms ? (latestRun.duration_ms / 1000).toFixed(2) + 's' : '—' }}</strong></span>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <a
                [routerLink]="['/evaluations', latestRun.id]"
                class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-gray-200 transition-colors border border-gray-700/60"
              >
                Inspect Details & Case Results →
              </a>
            </div>
          </div>

          <!-- Primary Metric Cards -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <!-- Finding Precision -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Finding Precision</span>
              <div class="text-2xl font-bold text-white font-mono mt-1">
                {{ formatPercent(latestRun.metrics.finding_precision) }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">TP / (TP + FP) finding accuracy</p>
            </div>

            <!-- Finding Recall -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Finding Recall</span>
              <div class="text-2xl font-bold text-white font-mono mt-1">
                {{ formatPercent(latestRun.metrics.finding_recall) }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">TP / (TP + FN) violations caught</p>
            </div>

            <!-- Finding F1 -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Finding F1 Score</span>
              <div class="text-2xl font-bold text-blue-400 font-mono mt-1">
                {{ latestRun.metrics.finding_f1 !== undefined && latestRun.metrics.finding_f1 !== null ? latestRun.metrics.finding_f1.toFixed(2) : 'N/A' }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">Harmonic mean of precision & recall</p>
            </div>

            <!-- Evidence Support Rate -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Evidence Grounding</span>
              <div class="text-2xl font-bold text-emerald-400 font-mono mt-1">
                {{ formatPercent(latestRun.metrics.evidence_support_rate) }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">Findings backed by timestamped proof</p>
            </div>

            <!-- Unsupported Findings -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Unsupported Rate</span>
              <div class="text-2xl font-bold text-white font-mono mt-1">
                {{ formatPercent(latestRun.metrics.unsupported_finding_rate) }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">Findings without direct grounding</p>
            </div>

            <!-- Citation Presence -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Citation Presence</span>
              <div class="text-2xl font-bold text-white font-mono mt-1">
                {{ formatPercent(latestRun.metrics.citation_presence_rate) }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">Findings with policy references</p>
            </div>

            <!-- Schema Conformance -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Schema Validity</span>
              <div class="text-2xl font-bold text-white font-mono mt-1">
                {{ formatPercent(latestRun.metrics.schema_validity_rate) }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">Structured output validity</p>
            </div>

            <!-- Verifier Agreement -->
            <div class="bg-slate-950 p-4 rounded-lg border border-gray-800/80">
              <span class="text-xs text-gray-400 font-medium">Verifier Agreement</span>
              <div class="text-2xl font-bold text-indigo-400 font-mono mt-1">
                {{ latestRun.metrics.verifier_agreement_rate !== null && latestRun.metrics.verifier_agreement_rate !== undefined ? formatPercent(latestRun.metrics.verifier_agreement_rate) : 'N/A' }}
              </div>
              <p class="text-[11px] text-gray-400 mt-1">Agreement with expected critic verdict</p>
            </div>
          </div>
        </div>
      }

      <!-- Error Analysis & Discrepancies Section -->
      @if (latestRun) {
        <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 shadow-xl">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-lg font-bold text-white">Discrepancies & Error Analysis</h3>
              <p class="text-xs text-gray-400 mt-0.5">
                Observed deviations from benchmark labels (False Positives, False Negatives, Severity Mismatches, Unsupported Claims).
              </p>
            </div>
            <span class="px-2.5 py-1 rounded text-xs font-mono bg-slate-950 text-gray-300 border border-gray-800">
              {{ latestRun.discrepancies?.length || 0 }} Discrepancies
            </span>
          </div>

          @if (!latestRun.discrepancies || latestRun.discrepancies.length === 0) {
            <div class="bg-slate-950/60 border border-emerald-500/20 rounded-lg p-4 text-xs text-emerald-300 flex items-center gap-2">
              <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              <span>No errors or discrepancies observed across all evaluated benchmark cases in this run.</span>
            </div>
          } @else {
            <div class="overflow-x-auto rounded-lg border border-gray-800">
              <table class="w-full text-left text-xs">
                <thead class="bg-slate-950/80 text-gray-400 border-b border-gray-800 uppercase text-[11px] tracking-wider">
                  <tr>
                    <th class="p-3">Case ID</th>
                    <th class="p-3">Failure Type</th>
                    <th class="p-3">Expected</th>
                    <th class="p-3">Actual</th>
                    <th class="p-3">Observed Discrepancy</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-800/60 font-mono">
                  @for (d of latestRun.discrepancies; track d.case_id + d.failure_type) {
                    <tr class="hover:bg-slate-800/30 transition-colors">
                      <td class="p-3 font-semibold text-blue-400">{{ d.case_id }}</td>
                      <td class="p-3">
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          {{ d.failure_type }}
                        </span>
                      </td>
                      <td class="p-3 text-gray-300">{{ d.expected || '—' }}</td>
                      <td class="p-3 text-gray-300">{{ d.actual || '—' }}</td>
                      <td class="p-3 font-sans text-gray-200">{{ d.observed_discrepancy }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>
      }

      <!-- Historical Runs Table with Multi-Select Comparison -->
      <div class="bg-slate-900 border border-gray-800 rounded-xl p-6 shadow-xl">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-800 gap-3">
          <div>
            <h3 class="text-lg font-bold text-white">Historical Evaluation Runs</h3>
            <p class="text-xs text-gray-400 mt-0.5">
              Select any 2 runs to perform a side-by-side neutral comparison of metrics and pipeline configurations.
            </p>
          </div>

          <div class="flex items-center gap-3">
            <button
              (click)="openComparison()"
              [disabled]="selectedRunIds.size < 2 || isComparing"
              class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {{ isComparing ? 'Comparing...' : 'Compare Selected (' + selectedRunIds.size + ')' }}
            </button>
          </div>
        </div>

        @if (isLoadingRuns) {
          <div class="py-12 text-center text-gray-400 text-sm">
            <svg class="w-6 h-6 animate-spin mx-auto text-blue-400 mb-2" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Loading evaluation runs...
          </div>
        } @else if (runs.length === 0) {
          <div class="py-12 text-center text-gray-400 text-sm">
            No evaluation runs recorded yet. Click <strong>"Run Evaluation"</strong> above to execute the benchmark suite.
          </div>
        } @else {
          <div class="overflow-x-auto mt-4 rounded-lg border border-gray-800">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-950/80 text-gray-400 border-b border-gray-800 uppercase text-[11px] tracking-wider">
                <tr>
                  <th class="p-3 w-10 text-center">Select</th>
                  <th class="p-3">Run Name / ID</th>
                  <th class="p-3">Status</th>
                  <th class="p-3">Model</th>
                  <th class="p-3">Prompt / Config</th>
                  <th class="p-3 text-right">F1 Score</th>
                  <th class="p-3 text-right">Grounding</th>
                  <th class="p-3 text-right">Duration</th>
                  <th class="p-3 text-right">Date</th>
                  <th class="p-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/60 font-mono">
                @for (r of runs; track r.id) {
                  <tr class="hover:bg-slate-800/30 transition-colors">
                    <td class="p-3 text-center">
                      <input
                        type="checkbox"
                        [checked]="selectedRunIds.has(r.id)"
                        (change)="toggleRunSelection(r.id)"
                        class="rounded border-gray-700 bg-slate-950 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        aria-label="Select run for comparison"
                      />
                    </td>
                    <td class="p-3 font-sans">
                      <div class="font-semibold text-white">{{ r.run_name }}</div>
                      <div class="text-[11px] text-gray-500 font-mono">{{ r.id | slice:0:8 }}</div>
                    </td>
                    <td class="p-3">
                      <span
                        class="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
                        [ngClass]="{
                          'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20': r.status === 'COMPLETED',
                          'bg-blue-500/10 text-blue-400 border border-blue-500/20': r.status === 'RUNNING' || r.status === 'QUEUED',
                          'bg-rose-500/10 text-rose-400 border border-rose-500/20': r.status === 'FAILED'
                        }"
                      >
                        {{ r.status }}
                      </span>
                    </td>
                    <td class="p-3 text-gray-300 font-mono">{{ r.model_name }}</td>
                    <td class="p-3 text-gray-400 font-mono">{{ r.prompt_version }} / {{ r.config_version }}</td>
                    <td class="p-3 text-right text-blue-400 font-bold">
                      {{ r.metrics.finding_f1 !== undefined && r.metrics.finding_f1 !== null ? r.metrics.finding_f1.toFixed(2) : '—' }}
                    </td>
                    <td class="p-3 text-right text-emerald-400 font-medium">
                      {{ formatPercent(r.metrics.evidence_support_rate) }}
                    </td>
                    <td class="p-3 text-right text-gray-400">
                      {{ r.duration_ms ? (r.duration_ms / 1000).toFixed(1) + 's' : '—' }}
                    </td>
                    <td class="p-3 text-right text-gray-500 font-sans">
                      {{ r.created_at ? (r.created_at | date:'short') : '—' }}
                    </td>
                    <td class="p-3 text-center font-sans">
                      <a
                        [routerLink]="['/evaluations', r.id]"
                        class="text-blue-400 hover:text-blue-300 font-semibold hover:underline"
                      >
                        Details
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

      <!-- Run Comparison Modal Component -->
      <app-run-comparison
        [comparison]="activeComparison"
        [visible]="isComparisonModalOpen"
        (close)="isComparisonModalOpen = false"
      ></app-run-comparison>
    </div>
  `
})
export class EvaluationsDashboardComponent implements OnInit, OnDestroy {
  private evalService = inject(EvaluationService);
  private pollSub?: Subscription;

  runs: EvaluationRun[] = [];
  latestRun: EvaluationRun | null = null;
  activeRun: EvaluationRun | null = null;

  isLoadingRuns = false;
  isTriggering = false;
  isRunning = false;

  selectedRunIds = new Set<string>();
  isComparing = false;
  isComparisonModalOpen = false;
  activeComparison: EvaluationComparison | null = null;

  ngOnInit(): void {
    this.loadRuns();
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  loadRuns(): void {
    this.isLoadingRuns = true;
    this.evalService.listRuns().subscribe({
      next: (runs) => {
        this.runs = runs;
        this.isLoadingRuns = false;
        if (runs.length > 0) {
          // If latest completed run is available, pick it
          this.latestRun = runs.find(r => r.status === 'COMPLETED') || runs[0];
          // Check if any run is currently RUNNING or QUEUED
          const running = runs.find(r => r.status === 'RUNNING' || r.status === 'QUEUED');
          if (running && !this.isRunning) {
            this.startPollingRun(running.id);
          }
        }
      },
      error: (err) => {
        console.error('Failed to load evaluation runs:', err);
        this.isLoadingRuns = false;
      }
    });
  }

  triggerEvaluationRun(): void {
    this.isTriggering = true;
    this.evalService.createRun({
      run_name: `Benchmark Run (${new Date().toLocaleTimeString()})`
    }).subscribe({
      next: (resp) => {
        this.isTriggering = false;
        this.isRunning = true;
        this.startPollingRun(resp.id);
      },
      error: (err) => {
        console.error('Failed to trigger evaluation run:', err);
        this.isTriggering = false;
      }
    });
  }

  startPollingRun(runId: string): void {
    this.isRunning = true;
    this.pollSub?.unsubscribe();
    this.pollSub = this.evalService.pollRun(runId, 2000).subscribe({
      next: (run) => {
        this.activeRun = run;
        if (run.status === 'COMPLETED' || run.status === 'FAILED') {
          this.isRunning = false;
          this.loadRuns();
        }
      },
      error: (err) => {
        console.error('Error polling evaluation run:', err);
        this.isRunning = false;
        this.loadRuns();
      }
    });
  }

  toggleRunSelection(runId: string): void {
    if (this.selectedRunIds.has(runId)) {
      this.selectedRunIds.delete(runId);
    } else {
      if (this.selectedRunIds.size >= 2) {
        // Limit to 2 for clear pairwise comparison or toggle
        const first = this.selectedRunIds.values().next().value;
        if (first) this.selectedRunIds.delete(first);
      }
      this.selectedRunIds.add(runId);
    }
  }

  openComparison(): void {
    if (this.selectedRunIds.size < 2) return;
    this.isComparing = true;
    const ids = Array.from(this.selectedRunIds);
    this.evalService.compareRuns(ids).subscribe({
      next: (comp) => {
        this.activeComparison = comp;
        this.isComparisonModalOpen = true;
        this.isComparing = false;
      },
      error: (err) => {
        console.error('Failed to compare runs:', err);
        this.isComparing = false;
      }
    });
  }

  formatPercent(val?: number | null): string {
    if (val === null || val === undefined) return 'N/A';
    return (val * 100).toFixed(0) + '%';
  }
}
