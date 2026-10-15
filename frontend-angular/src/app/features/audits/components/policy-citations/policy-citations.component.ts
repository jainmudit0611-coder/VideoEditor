import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { Citation } from '../../../../core/models/audit.model';

@Component({
  selector: 'app-policy-citations',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (!citations || citations.length === 0) {
      <div class="glass-panel p-5 rounded-xl border border-gray-800">
        <h4 class="text-sm font-semibold text-white flex items-center gap-2 mb-2">
          <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
          </svg>
          <span>Policy / RAG Citations</span>
        </h4>
        <p class="text-xs text-gray-400 italic">
          No policy reference citations attached to this report.
        </p>
      </div>
    } @else {
      <div class="glass-panel p-5 rounded-xl border border-gray-800 space-y-4">
        <div class="flex items-center justify-between border-b border-gray-800 pb-3">
          <h3 class="text-base font-semibold text-white flex items-center gap-2">
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
            </svg>
            <span>Policy / RAG Citations ({{ citations.length }})</span>
          </h3>
          <span class="text-xs text-blue-400 font-mono">Azure AI Search / Policy Vector DB</span>
        </div>

        <div class="space-y-3">
          @for (cite of citations; track $index) {
            <div class="p-4 rounded-xl bg-slate-950/80 border border-gray-800 space-y-2 hover:border-gray-700 transition-colors">
              <div class="flex items-center justify-between text-xs">
                <div class="flex items-center gap-2 text-blue-400 font-semibold">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
                  </svg>
                  <span>{{ cite.policy_name || cite.source || 'Compliance Policy Document' }}</span>
                </div>

                @if (cite.relevance_score !== undefined && cite.relevance_score !== null) {
                  <span class="text-[11px] font-mono text-gray-400">
                    Relevance: <strong class="text-emerald-400">{{ (cite.relevance_score * 100).toFixed(0) }}%</strong>
                  </span>
                }
              </div>

              <p class="text-xs text-gray-300 leading-relaxed font-sans">
                {{ cite.rule_text || cite.content || stringify(cite) }}
              </p>

              @if (cite.source) {
                <div class="flex items-center gap-1 text-[11px] text-gray-500 font-mono pt-1">
                  <svg class="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                  </svg>
                  <span>Source Vector Document: {{ cite.source }}</span>
                </div>
              }
            </div>
          }
        </div>
      </div>
    }
  `
})
export class PolicyCitationsComponent {
  @Input() citations?: Citation[];

  stringify(val: any): string {
    return typeof val === 'string' ? val : JSON.stringify(val);
  }
}
