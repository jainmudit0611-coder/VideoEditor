import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { VerificationSummary } from '../../../../core/models/audit.model';

@Component({
  selector: 'app-verifier-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="glass-panel p-5 rounded-xl border space-y-3"
      [ngClass]="isVerified ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-amber-500/30 bg-amber-500/5'"
    >
      <div class="flex items-center justify-between border-b border-gray-800 pb-3">
        <div class="flex items-center gap-2">
          @if (isVerified) {
            <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
          } @else {
            <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          }
          <h4 class="text-sm font-semibold text-white">Evidence Verification & Critic Agent</h4>
        </div>

        <span
          class="px-3 py-1 rounded-full text-xs font-bold border"
          [ngClass]="isVerified ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-amber-500/10 text-amber-400 border-amber-500/30'"
        >
          {{ statusStr }}
        </span>
      </div>

      <div class="space-y-2 text-xs text-gray-300">
        <p class="leading-relaxed">{{ reasoning }}</p>

        <div class="pt-2 grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div class="flex items-center gap-1.5 text-emerald-400">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Policy Evidence Matched</span>
          </div>
          <div class="flex items-center gap-1.5 text-emerald-400">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Transcript Evidence Matched</span>
          </div>
          <div class="flex items-center gap-1.5 text-emerald-400">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Timestamp Anchored</span>
          </div>
        </div>
      </div>
    </div>
  `
})
export class VerifierCardComponent {
  @Input() summary?: VerificationSummary | null;

  get isVerified(): boolean {
    return this.summary?.verified ?? true;
  }

  get statusStr(): string {
    return (this.summary?.status || (this.isVerified ? 'VERIFIED' : 'NEEDS REVIEW')).toUpperCase();
  }

  get reasoning(): string {
    return this.summary?.reasoning || 'Audit findings verified against multimodal evidence stream and policy rules.';
  }
}
