import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-[#090D16] text-gray-100 flex flex-col justify-center items-center p-4 sm:p-6 lg:p-8">
      <!-- Glow effect -->
      <div class="absolute w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none -top-20 -left-20"></div>
      <div class="absolute w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -bottom-20 -right-20"></div>

      <div class="relative w-full max-w-md">
        <!-- Brand Header -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center bg-gradient-to-tr from-blue-600 to-cyan-500 p-3 rounded-xl shadow-lg shadow-blue-500/25 mb-4">
            <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-white tracking-tight">Create Account</h1>
          <p class="text-sm text-gray-400 mt-1">Join Brand Guardian AI Compliance Platform</p>
        </div>

        <!-- Register Card -->
        <div class="glass-panel p-6 sm:p-8 rounded-2xl border border-gray-800 shadow-2xl bg-slate-900/80 backdrop-blur-xl">
          <div class="mb-6">
            <h2 class="text-lg font-semibold text-white">Get Started</h2>
            <p class="text-xs text-gray-400 mt-1">Set up your compliance officer profile</p>
          </div>

          <!-- Error Alert -->
          @if (errorMessage()) {
            <div class="mb-5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2.5">
              <svg class="w-4 h-4 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>{{ errorMessage() }}</span>
            </div>
          }

          <form (ngSubmit)="onSubmit()" class="space-y-4">
            <div>
              <label for="displayName" class="block text-xs font-medium text-gray-300 mb-1.5">Full Name</label>
              <input
                id="displayName"
                type="text"
                name="displayName"
                [(ngModel)]="displayName"
                required
                autocomplete="name"
                placeholder="Jane Doe"
                class="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-gray-800 text-sm text-white placeholder-gray-500 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                [disabled]="isLoading()"
              />
            </div>

            <div>
              <label for="email" class="block text-xs font-medium text-gray-300 mb-1.5">Email Address</label>
              <input
                id="email"
                type="email"
                name="email"
                [(ngModel)]="email"
                required
                autocomplete="email"
                placeholder="jane@example.com"
                class="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-gray-800 text-sm text-white placeholder-gray-500 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                [disabled]="isLoading()"
              />
            </div>

            <div>
              <label for="password" class="block text-xs font-medium text-gray-300 mb-1.5">Password</label>
              <input
                id="password"
                type="password"
                name="password"
                [(ngModel)]="password"
                required
                minlength="6"
                autocomplete="new-password"
                placeholder="••••••••"
                class="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-gray-800 text-sm text-white placeholder-gray-500 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                [disabled]="isLoading()"
              />
              <span class="text-[10px] text-gray-500 mt-1 block">Must be at least 6 characters</span>
            </div>

            <div>
              <label for="confirmPassword" class="block text-xs font-medium text-gray-300 mb-1.5">Confirm Password</label>
              <input
                id="confirmPassword"
                type="password"
                name="confirmPassword"
                [(ngModel)]="confirmPassword"
                required
                autocomplete="new-password"
                placeholder="••••••••"
                class="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-gray-800 text-sm text-white placeholder-gray-500 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                [disabled]="isLoading()"
              />
            </div>

            <button
              type="submit"
              [disabled]="isLoading() || !displayName || !email || !password || !confirmPassword"
              class="w-full mt-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-medium text-sm shadow-md shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 flex items-center justify-center gap-2"
            >
              @if (isLoading()) {
                <svg class="animate-spin w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Creating account...</span>
              } @else {
                <span>Create Account</span>
              }
            </button>
          </form>

          <div class="mt-6 pt-5 border-t border-gray-800/80 text-center">
            <p class="text-xs text-gray-400">
              Already have an account?
              <a routerLink="/login" class="text-blue-400 hover:text-blue-300 font-medium ml-1 transition-colors">
                Sign In
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  `
})
export class RegisterComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  displayName = '';
  email = '';
  password = '';
  confirmPassword = '';
  errorMessage = signal<string | null>(null);

  get isLoading() {
    return this.authService.isLoading;
  }

  onSubmit(): void {
    if (!this.displayName.trim() || !this.email.trim() || !this.password) {
      this.errorMessage.set('All fields are required.');
      return;
    }

    if (this.password.length < 6) {
      this.errorMessage.set('Password must be at least 6 characters long.');
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.errorMessage.set('Passwords do not match.');
      return;
    }

    this.errorMessage.set(null);
    this.authService.register({
      display_name: this.displayName.trim(),
      email: this.email.trim(),
      password: this.password
    }).subscribe({
      next: () => {
        // Automatically authenticate user upon successful registration
        this.authService.login({
          email: this.email.trim(),
          password: this.password
        }).subscribe({
          next: () => this.router.navigate(['/dashboard']),
          error: () => this.router.navigate(['/login'])
        });
      },
      error: (err) => {
        let msg = 'Registration failed. Please try again.';
        if (err.error && typeof err.error === 'object' && err.error.detail) {
          msg = err.error.detail;
        } else if (err.status === 409) {
          msg = 'An account with this email address already exists.';
        }
        this.errorMessage.set(msg);
      }
    });
  }
}
