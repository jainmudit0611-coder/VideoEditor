import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { HeaderComponent } from '../header/header.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { HealthService } from '../../core/services/health.service';
import type { ReadinessStatus } from '../../core/models/api.model';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, HeaderComponent, SidebarComponent],
  template: `
    @if (isAuthPage()) {
      <main class="min-h-screen bg-[#090D16]">
        <router-outlet></router-outlet>
      </main>
    } @else {
      <div class="min-h-screen bg-[#090D16] text-gray-100 flex flex-col font-sans">
        <app-header
          [readiness]="readiness()"
          (toggleSidebar)="sidebarOpen.set(!sidebarOpen())"
        ></app-header>

        <div class="flex-1 flex max-w-7xl w-full mx-auto">
          <app-sidebar
            [readiness]="readiness()"
            [isOpen]="sidebarOpen()"
            (close)="sidebarOpen.set(false)"
          ></app-sidebar>

          <main class="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-full">
            <router-outlet></router-outlet>
          </main>
        </div>
      </div>
    }
  `
})
export class LayoutComponent {
  private healthService = inject(HealthService);
  private router = inject(Router);

  readiness = signal<ReadinessStatus | null>(null);
  sidebarOpen = signal<boolean>(false);
  isAuthPage = signal<boolean>(false);

  constructor() {
    this.checkIfAuthPage(this.router.url);

    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd)
    ).subscribe((event: NavigationEnd) => {
      this.checkIfAuthPage(event.urlAfterRedirects || event.url);
    });

    this.healthService.pollReadiness().subscribe({
      next: (status) => this.readiness.set(status),
      error: () => this.readiness.set(null)
    });
  }

  private checkIfAuthPage(url: string): void {
    const isAuth = url.includes('/login') || url.includes('/register');
    this.isAuthPage.set(isAuth);
  }
}

