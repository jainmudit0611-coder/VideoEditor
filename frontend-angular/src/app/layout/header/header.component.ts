import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { ReadinessStatus } from '../../core/models/api.model';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    <header class="sticky top-0 z-30 bg-slate-900/90 backdrop-blur-md border-b border-gray-800 px-4 sm:px-6 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button
          (click)="toggleSidebar.emit()"
          class="md:hidden p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors"
          aria-label="Toggle Navigation"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>
        <div class="flex items-center gap-2.5">
          <div class="bg-gradient-to-tr from-blue-600 to-cyan-500 p-2 rounded-lg shadow-md shadow-blue-500/20">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
          </div>
          <div>
            <span class="font-bold text-base sm:text-lg text-white tracking-tight">Brand Guardian AI</span>
            <span class="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              v3.0 Production
            </span>
          </div>
        </div>
      </div>

      <!-- Right Section: System Status & User Profile -->
      <div class="flex items-center gap-3 sm:gap-4 text-xs font-medium">
        <!-- System Status Indicators -->
        <div class="hidden xl:flex items-center gap-4 text-gray-400 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-gray-800">
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/>
            </svg>
            <span>API: <strong class="text-gray-200">Online</strong></span>
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/>
            </svg>
            <span>DB: <strong [ngClass]="readiness?.database === 'ok' ? 'text-emerald-400' : 'text-rose-400'">{{ readiness?.database || '—' }}</strong></span>
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            <span>Redis: <strong [ngClass]="readiness?.redis === 'ok' ? 'text-emerald-400' : 'text-amber-400'">{{ readiness?.redis || '—' }}</strong></span>
          </div>
        </div>

        <!-- Global Status Pill -->
        <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-950 border border-gray-800 text-xs">
          <span
            class="w-2 h-2 rounded-full"
            [ngClass]="isReady ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'"
          ></span>
          <span class="text-gray-300">
            System {{ isReady ? 'Healthy' : 'Degraded' }}
          </span>
        </div>

        <!-- Authenticated User & Logout -->
        @if (currentUser()) {
          <div class="flex items-center gap-2.5 sm:gap-3 pl-3 sm:pl-4 border-l border-gray-800">
            <div class="flex flex-col items-end">
              <span class="text-xs font-semibold text-white leading-tight">{{ currentUser()?.display_name }}</span>
              <div class="flex items-center gap-1 mt-0.5">
                <span
                  class="text-[9px] font-mono px-1.5 py-0.2 rounded font-semibold uppercase tracking-wider"
                  [ngClass]="currentUser()?.role === 'ADMIN' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'bg-blue-500/10 text-cyan-400 border border-cyan-500/20'"
                >
                  {{ currentUser()?.role }}
                </span>
              </div>
            </div>
            <button
              (click)="logout()"
              class="px-2.5 py-1.5 rounded-lg bg-gray-800/80 hover:bg-rose-500/20 hover:text-rose-300 text-gray-300 border border-gray-700/60 hover:border-rose-500/30 text-xs font-medium transition-colors flex items-center gap-1.5"
              title="Sign Out"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              <span class="hidden md:inline">Sign Out</span>
            </button>
          </div>
        }
      </div>
    </header>
  `
})
export class HeaderComponent {
  private authService = inject(AuthService);

  @Input() readiness: ReadinessStatus | null = null;
  @Output() toggleSidebar = new EventEmitter<void>();

  currentUser = this.authService.currentUser;

  get isReady(): boolean {
    return this.readiness?.status === 'ready';
  }

  logout(): void {
    this.authService.logout();
  }
}
