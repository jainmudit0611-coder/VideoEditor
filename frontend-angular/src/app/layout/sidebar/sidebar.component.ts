import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import type { ReadinessStatus } from '../../core/models/api.model';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <!-- Mobile Backdrop -->
    @if (isOpen) {
      <div
        (click)="close.emit()"
        class="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs md:hidden"
      ></div>
    }

    <aside
      class="fixed md:sticky top-[57px] left-0 z-40 w-64 h-[calc(100vh-57px)] bg-slate-900/95 border-r border-gray-800 flex flex-col justify-between p-4 transition-transform duration-200 ease-in-out"
      [ngClass]="isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
    >
      <div class="space-y-6">
        <div class="px-3 py-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Navigation
          </span>
        </div>

        <nav class="space-y-1">
          <a
            routerLink="/dashboard"
            routerLinkActive="bg-blue-600/15 text-blue-400 border border-blue-500/30"
            [routerLinkActiveOptions]="{ exact: true }"
            (click)="close.emit()"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-gray-300 hover:bg-gray-800/60 hover:text-white"
          >
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
            </svg>
            <span>Dashboard</span>
          </a>

          <a
            routerLink="/audits/new"
            routerLinkActive="bg-blue-600/15 text-blue-400 border border-blue-500/30"
            (click)="close.emit()"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-gray-300 hover:bg-gray-800/60 hover:text-white"
          >
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>New Audit</span>
          </a>

          <a
            routerLink="/evaluations"
            routerLinkActive="bg-blue-600/15 text-blue-400 border border-blue-500/30"
            (click)="close.emit()"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-gray-300 hover:bg-gray-800/60 hover:text-white"
          >
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
            </svg>
            <span>Evaluations</span>
          </a>

          <a
            routerLink="/dashboard"
            fragment="history"
            (click)="close.emit()"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-gray-300 hover:bg-gray-800/60 hover:text-white cursor-pointer"
          >
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Audit History</span>
          </a>
        </nav>
      </div>

      <!-- System Architecture & Health Details -->
      <div class="space-y-4 pt-4 border-t border-gray-800 text-xs">
        <div class="px-3">
          <span class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
            Backend Architecture
          </span>
        </div>

        <div class="space-y-2 bg-slate-950/70 p-3 rounded-lg border border-gray-800/80">
          <div class="flex items-center justify-between">
            <span class="flex items-center gap-2 text-gray-300">
              <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
              </svg>
              LangGraph Engine
            </span>
            <span class="text-[10px] text-emerald-400 font-mono">v1.2</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="flex items-center gap-2 text-gray-300">
              <svg class="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/>
              </svg>
              PostgreSQL DB
            </span>
            <span class="text-[10px] text-emerald-400 font-mono">
              {{ readiness?.database === 'ok' ? 'Connected' : 'Offline' }}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="flex items-center gap-2 text-gray-300">
              <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              Redis Queue
            </span>
            <span class="text-[10px] text-amber-400 font-mono">
              {{ readiness?.redis === 'ok' ? 'Redis' : readiness?.redis === 'memory_fallback_active' ? 'In-Memory' : 'Off' }}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="flex items-center gap-2 text-gray-300">
              <svg class="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/>
              </svg>
              Vision Mode
            </span>
            <span class="text-[10px] text-purple-400 font-mono">Multimodal</span>
          </div>
        </div>

        <div class="px-3 text-[11px] text-gray-400">
          Brand Guardian AI © 2026
        </div>
      </div>
    </aside>
  `
})
export class SidebarComponent {
  @Input() readiness: ReadinessStatus | null = null;
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
}
