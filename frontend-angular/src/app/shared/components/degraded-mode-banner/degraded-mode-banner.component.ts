import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-degraded-mode-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (isDegraded) {
      <div class="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-6 text-amber-200">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <div class="space-y-1 text-sm">
            <div class="flex items-center gap-2 font-semibold text-amber-300">
              <span>Execution Mode: DEGRADED OCR FALLBACK</span>
            </div>
            <p class="text-amber-200/80 leading-relaxed">
              Native vision analysis was not available for this run. Visual observations were derived using the fallback OCR & transcript heuristic engine.
            </p>
          </div>
        </div>
      </div>
    } @else {
      <div class="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 mb-6 text-emerald-200">
        <div class="flex items-center gap-3 text-xs sm:text-sm">
          <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
          </svg>
          <span class="font-medium text-emerald-300">
            Execution Mode: NATIVE VISION (Full Multimodal Extraction Active)
          </span>
        </div>
      </div>
    }
  `
})
export class DegradedModeBannerComponent {
  @Input() isDegraded = false;
}
