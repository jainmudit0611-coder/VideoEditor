import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from './auth.service';
import type { User, TokenResponse } from '../models/auth.model';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let router: Router;

  const mockUser: User = {
    id: 'user-uuid-1',
    email: 'officer@brandguardian.ai',
    display_name: 'Compliance Officer',
    role: 'USER',
    is_active: true,
    created_at: '2026-09-23T12:00:00Z'
  };

  const mockTokenResponse: TokenResponse = {
    access_token: 'fake-jwt-token-xyz',
    token_type: 'bearer'
  };

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created with initial unauthenticated state', () => {
    expect(service).toBeTruthy();
    expect(service.currentUser()).toBeNull();
    expect(service.getAccessToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('should authenticate user and store token on successful login', () => {
    service.login({ email: 'officer@brandguardian.ai', password: 'password123' }).subscribe(user => {
      expect(user).toEqual(mockUser);
      expect(service.currentUser()).toEqual(mockUser);
      expect(service.getAccessToken()).toBe('fake-jwt-token-xyz');
      expect(service.isAuthenticated()).toBe(true);
    });

    // 1. Expect login call
    const loginReq = httpMock.expectOne('http://localhost:8000/auth/login');
    expect(loginReq.request.method).toBe('POST');
    expect(loginReq.request.body).toEqual({ email: 'officer@brandguardian.ai', password: 'password123' });
    loginReq.flush(mockTokenResponse);

    // 2. Expect loadCurrentUser call
    const meReq = httpMock.expectOne('http://localhost:8000/auth/me');
    expect(meReq.request.method).toBe('GET');
    meReq.flush(mockUser);
  });

  it('should handle login failure and not set user or token', () => {
    let errorOccurred = false;
    service.login({ email: 'officer@brandguardian.ai', password: 'wrong' }).subscribe({
      next: () => {},
      error: (err) => {
        errorOccurred = true;
        expect(err.status).toBe(401);
      }
    });

    const loginReq = httpMock.expectOne('http://localhost:8000/auth/login');
    loginReq.flush({ detail: 'Incorrect email or password' }, { status: 401, statusText: 'Unauthorized' });

    expect(errorOccurred).toBe(true);
    expect(service.currentUser()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('should register a new user successfully', () => {
    const registerData = {
      email: 'newuser@brandguardian.ai',
      password: 'password123',
      display_name: 'New User'
    };

    service.register(registerData).subscribe(user => {
      expect(user.id).toBe('user-uuid-1');
      expect(user.email).toBe('newuser@brandguardian.ai');
    });

    const req = httpMock.expectOne('http://localhost:8000/auth/register');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(registerData);
    req.flush({ ...mockUser, email: 'newuser@brandguardian.ai', display_name: 'New User' });
  });

  it('should handle registration failure (e.g., 409 conflict)', () => {
    let errorStatus = 0;
    service.register({
      email: 'existing@brandguardian.ai',
      password: 'password123',
      display_name: 'Existing'
    }).subscribe({
      next: () => {},
      error: (err) => {
        errorStatus = err.status;
      }
    });

    const req = httpMock.expectOne('http://localhost:8000/auth/register');
    req.flush({ detail: 'Email already registered' }, { status: 409, statusText: 'Conflict' });

    expect(errorStatus).toBe(409);
  });

  it('should fetch and set current user with loadCurrentUser', () => {
    service.loadCurrentUser().subscribe(user => {
      expect(user).toEqual(mockUser);
      expect(service.currentUser()).toEqual(mockUser);
    });

    const req = httpMock.expectOne('http://localhost:8000/auth/me');
    expect(req.request.method).toBe('GET');
    req.flush(mockUser);
  });

  it('should clear session and navigate to /login on logout', () => {
    const navSpy = vi.spyOn(router, 'navigate');

    // Simulate authenticated state
    localStorage.setItem('bg_auth_token', 'test-token');
    service.currentUser.set(mockUser);
    service.token.set('test-token');

    expect(service.isAuthenticated()).toBe(true);

    service.logout();

    expect(service.currentUser()).toBeNull();
    expect(service.getAccessToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('bg_auth_token')).toBeNull();
    expect(navSpy).toHaveBeenCalledWith(['/login']);
  });

  it('should restore authenticated state in initAuth if valid token is stored', () => {
    localStorage.setItem('bg_auth_token', 'stored-token-123');
    const newService = TestBed.inject(AuthService);

    newService.initAuth().subscribe(user => {
      expect(user).toEqual(mockUser);
      expect(newService.currentUser()).toEqual(mockUser);
    });

    const req = httpMock.expectOne('http://localhost:8000/auth/me');
    req.flush(mockUser);
    expect(newService.isInitialized()).toBe(true);
  });

  it('should clear session in initAuth if stored token is rejected by backend', () => {
    localStorage.setItem('bg_auth_token', 'expired-token');
    const newService = TestBed.inject(AuthService);

    newService.initAuth().subscribe(user => {
      expect(user).toBeNull();
      expect(newService.currentUser()).toBeNull();
      expect(newService.getAccessToken()).toBeNull();
    });

    const req = httpMock.expectOne('http://localhost:8000/auth/me');
    req.flush({ detail: 'Token expired' }, { status: 401, statusText: 'Unauthorized' });
    expect(newService.isInitialized()).toBe(true);
  });
});
