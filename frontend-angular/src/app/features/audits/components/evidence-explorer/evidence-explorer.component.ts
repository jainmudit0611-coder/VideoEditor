import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { AuditResult, EvidenceItem } from '../../../../core/models/audit.model';

@Component({
  selector: 'app-evidence-explorer',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (result) {
      <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800 pb-4">
          <div>
            <h3 class="text-base font-semibold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
              </svg>
              <span>Multimodal Evidence Explorer</span>
            </h3>
            <p class="text-xs text-gray-400 mt-0.5">
              Temporal evidence extracted across audio, frame OCR, and vision streams
            </p>
          </div>

          <!-- Evidence Category Tabs -->
          <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-gray-800 self-start sm:self-auto">
            <button
              (click)="activeTab.set('TRANSCRIPT')"
              class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer"
              [ngClass]="activeTab() === 'TRANSCRIPT' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-white'"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <span>Transcript ({{ combinedTranscript.length }})</span>
            </button>

            <button
              (click)="activeTab.set('OCR')"
              class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer"
              [ngClass]="activeTab() === 'OCR' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-white'"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>
              </svg>
              <span>OCR ({{ combinedOcr.length }})</span>
            </button>

            <button
              (click)="activeTab.set('VISUAL')"
              class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer"
              [ngClass]="activeTab() === 'VISUAL' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-400 hover:text-white'"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
              <span>Visual ({{ combinedVisual.length }})</span>
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <div class="space-y-3">
          @if (activeTab() === 'VISUAL' && isDegraded && combinedVisual.length === 0) {
            <div class="bg-amber-500/10 border border-amber-500/30 rounded-xl p-5 text-amber-200 text-sm space-y-2">
              <div class="flex items-center gap-2 font-semibold text-amber-300">
                <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <span>Visual analysis unavailable</span>
              </div>
              <p class="text-xs text-amber-200/80 leading-relaxed">
                The current audit ran in <strong>DEGRADED_OCR_FALLBACK</strong> mode. Native vision analysis was not available during pipeline invocation.
              </p>
            </div>
          } @else if (currentItems.length === 0) {
            <div class="text-center py-8 text-xs text-gray-500 bg-slate-950/40 rounded-xl border border-gray-800/80">
              No {{ activeTab().toLowerCase() }} evidence records captured for this video.
            </div>
          } @else {
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              @for (item of currentItems; track $index) {
                <div class="p-4 rounded-xl bg-slate-950/70 border border-gray-800 hover:border-gray-700 transition-colors space-y-2">
                  <div class="flex items-center justify-between text-xs">
                    <span class="flex items-center gap-1.5 font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                      <span>{{ item.timestamp || '00:00' }}</span>
                    </span>

                    <span class="font-mono text-[11px] text-gray-400">
                      Confidence: <strong class="text-emerald-400">{{ ((item.confidence ?? 0.9) * 100).toFixed(0) }}%</strong>
                    </span>
                  </div>

                  <p class="text-xs text-gray-200 leading-relaxed font-sans">
                    "{{ item.content }}"
                  </p>

                  @if (item.source) {
                    <div class="text-[11px] text-gray-500 flex items-center gap-1 font-mono pt-1">
                      <span>Source: {{ item.source }}</span>
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      </div>
    }
  `
})
export class EvidenceExplorerComponent {
  @Input() result?: AuditResult | null;
  @Input() isDegraded = false;
  activeTab = signal<'TRANSCRIPT' | 'OCR' | 'VISUAL'>('TRANSCRIPT');

  get combinedTranscript(): EvidenceItem[] {
    if (!this.result) return [];
    if (this.result.transcript_items?.length) return this.result.transcript_items;
    return (this.result.retrieved_evidence || []).filter(e => (e.type || '').toUpperCase() === 'TRANSCRIPT');
  }

  get combinedOcr(): EvidenceItem[] {
    if (!this.result) return [];
    if (this.result.ocr_items?.length) return this.result.ocr_items;
    return (this.result.retrieved_evidence || []).filter(e => (e.type || '').toUpperCase() === 'OCR');
  }

  get combinedVisual(): EvidenceItem[] {
    if (!this.result) return [];
    if (this.result.visual_observations?.length) return this.result.visual_observations;
    return (this.result.retrieved_evidence || []).filter(e => (e.type || '').toUpperCase() === 'VISUAL');
  }

  get currentItems(): EvidenceItem[] {
    switch (this.activeTab()) {
      case 'TRANSCRIPT':
        return this.combinedTranscript;
      case 'OCR':
        return this.combinedOcr;
      case 'VISUAL':
        return this.combinedVisual;
      default:
        return [];
    }
  }
}
