import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { tap, catchError, map, finalize, switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import type { User, TokenResponse, LoginRequest, RegisterRequest } from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private baseUrl = environment.apiBaseUrl;
  private readonly TOKEN_STORAGE_KEY = 'bg_auth_token';

  // --- Reactive Authentication State ---
  currentUser = signal<User | null>(null);
  token = signal<string | null>(this.getStoredToken());
  isAuthenticated = computed(() => !!this.currentUser() && !!this.token());
  isLoading = signal<boolean>(false);
  isInitialized = signal<boolean>(false);

  private getStoredToken(): string | null {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return localStorage.getItem(this.TOKEN_STORAGE_KEY);
      }
    } catch {
      // Storage access may fail in private mode or non-browser environments
    }
    return null;
  }

  private setStoredToken(token: string | null): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        if (token) {
          localStorage.setItem(this.TOKEN_STORAGE_KEY, token);
        } else {
          localStorage.removeItem(this.TOKEN_STORAGE_KEY);
        }
      }
    } catch {
      // Ignore storage errors safely
    }
    this.token.set(token);
  }

  /**
   * Initializes session on application startup by validating any existing stored token.
   */
  initAuth(): Observable<User | null> {
    const savedToken = this.getStoredToken();
    if (!savedToken) {
      this.isInitialized.set(true);
      return of(null);
    }

    return this.loadCurrentUser().pipe(
      map(user => user),
      catchError(() => {
        this.clearSession();
        return of(null);
      }),
      finalize(() => {
        this.isInitialized.set(true);
      })
    );
  }

  /**
   * Authenticates user credentials with the backend, stores the JWT,
   * and loads the active user profile.
   */
  login(credentials: LoginRequest): Observable<User> {
    this.isLoading.set(true);
    return this.http.post<TokenResponse>(`${this.baseUrl}/auth/login`, credentials).pipe(
      tap(response => {
        this.setStoredToken(response.access_token);
      }),
      switchMap(() => this.loadCurrentUser()),
      finalize(() => this.isLoading.set(false))
    );
  }

  /**
   * Registers a new user account with the backend.
   */
  register(data: RegisterRequest): Observable<User> {
    this.isLoading.set(true);
    return this.http.post<User>(`${this.baseUrl}/auth/register`, data).pipe(
      finalize(() => this.isLoading.set(false))
    );
  }

  /**
   * Fetches the current authenticated user profile from GET /auth/me.
   */
  loadCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/auth/me`).pipe(
      tap(user => {
        this.currentUser.set(user);
      }),
      catchError(err => {
        this.clearSession();
        return throwError(() => err);
      })
    );
  }

  /**
   * Clears all session credentials and navigates the user to /login.
   */
  logout(): void {
    this.clearSession();
    this.router.navigate(['/login']);
  }

  /**
   * Clears internal auth signals and removes the stored token.
   */
  clearSession(): void {
    this.setStoredToken(null);
    this.currentUser.set(null);
  }

  /**
   * Returns the current JWT access token string, if available.
   */
  getAccessToken(): string | null {
    return this.token();
  }
}
