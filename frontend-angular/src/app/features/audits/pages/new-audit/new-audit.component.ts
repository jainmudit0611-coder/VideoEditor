import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { AuditService } from '../../../../core/services/audit.service';
import { isValidHttpUrl } from '../../../../shared/utils/formatting.utils';

@Component({
  selector: 'app-new-audit',
  standalone: true,
  imports: [CommonModule, RouterModule, ReactiveFormsModule],
  template: `
    <div class="max-w-2xl mx-auto space-y-6">
      <!-- Top Back Navigation -->
      <a
        routerLink="/dashboard"
        class="inline-flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-white transition-colors cursor-pointer"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
        <span>Back to Dashboard</span>
      </a>

      <!-- Main Form Card -->
      <div class="glass-panel p-6 sm:p-8 rounded-2xl border border-gray-800 space-y-6">
        <div class="space-y-1">
          <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2.5">
            <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Audit a Video</span>
          </h1>
          <p class="text-xs text-gray-400 leading-relaxed">
            Enter a YouTube video URL to run an agentic compliance audit against FTC guidelines and brand disclosure policies.
          </p>
        </div>

        <form [formGroup]="auditForm" (ngSubmit)="onSubmit()" class="space-y-5">
          <div class="space-y-2">
            <label for="video-url" class="block text-xs font-semibold text-gray-300">
              Target Video URL <span class="text-rose-400">*</span>
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                </svg>
              </div>
              <input
                id="video-url"
                type="text"
                formControlName="videoUrl"
                placeholder="https://www.youtube.com/watch?v=..."
                class="w-full pl-10 pr-4 py-3 bg-slate-950 border border-gray-800 rounded-xl text-xs sm:text-sm text-white placeholder-gray-500 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              />
            </div>
          </div>

          @if (errorMessage()) {
            <div class="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-2.5 text-xs text-rose-300">
              <svg class="w-4 h-4 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>{{ errorMessage() }}</span>
            </div>
          }

          <div class="pt-2">
            <button
              type="submit"
              [disabled]="loading()"
              class="w-full flex items-center justify-center gap-2 py-3 px-5 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 disabled:opacity-50 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 transition-all cursor-pointer text-sm"
            >
              @if (loading()) {
                <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                <span>Enqueuing Audit Job...</span>
              } @else {
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
                <span>Start Audit</span>
              }
            </button>
          </div>
        </form>

        <div class="p-4 bg-slate-950/60 rounded-xl border border-gray-800/80 text-[11px] text-gray-400 space-y-1 font-mono">
          <div class="text-gray-300 font-semibold">Backend Asynchronous Processing:</div>
          <p>
            Submitting enqueues a job into Redis / PostgreSQL. The LangGraph compliance worker processes video indexing, visual OCR, and agent verification asynchronously.
          </p>
        </div>
      </div>
    </div>
  `
})
export class NewAuditComponent {
  private fb = inject(FormBuilder);
  private auditService = inject(AuditService);
  private router = inject(Router);

  loading = signal<boolean>(false);
  errorMessage = signal<string | null>(null);

  auditForm = this.fb.group({
    videoUrl: ['', [Validators.required]]
  });

  onSubmit(): void {
    const url = (this.auditForm.get('videoUrl')?.value || '').trim();

    if (!url) {
      this.errorMessage.set('Please enter a target video URL.');
      return;
    }

    if (!isValidHttpUrl(url)) {
      this.errorMessage.set('Please enter a valid HTTP or HTTPS video URL (e.g. https://www.youtube.com/watch?v=...).');
      return;
    }

    this.errorMessage.set(null);
    this.loading.set(true);

    this.auditService.createAudit(url).subscribe({
      next: (res) => {
        this.loading.set(false);
        if (res.audit_id) {
          this.router.navigate(['/audits', res.audit_id]);
        } else {
          this.errorMessage.set('No audit ID returned by backend.');
        }
      },
      error: (err) => {
        this.loading.set(false);
        this.errorMessage.set(err.message || 'Failed to submit audit job.');
      }
    });
  }
}
