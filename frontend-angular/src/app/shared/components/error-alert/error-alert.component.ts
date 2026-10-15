import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-error-alert',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-rose-200">
      <div class="flex items-start gap-3">
        <svg class="w-5 h-5 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div class="flex-1 space-y-1 text-sm">
          <div class="font-semibold text-rose-300">{{ title }}</div>
          <p class="text-rose-200/80 leading-relaxed break-words">{{ message }}</p>
        </div>
        @if (showRetry) {
          <button
            (click)="retry.emit()"
            class="flex items-center gap-1.5 text-xs font-medium bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 px-3 py-1.5 rounded-lg border border-rose-500/40 transition-colors shrink-0 cursor-pointer"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            <span>Retry</span>
          </button>
        }
      </div>
    </div>
  `
})
export class ErrorAlertComponent {
  @Input() title = 'Execution Error';
  @Input({ required: true }) message = '';
  @Input() showRetry = false;
  @Output() retry = new EventEmitter<void>();
}
