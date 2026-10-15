import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';

describe('authInterceptor', () => {
  let httpClient: HttpClient;
  let httpMock: HttpTestingController;
  let authService: AuthService;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting()
      ]
    });

    httpClient = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should not add Authorization header when no token is present', () => {
    authService.token.set(null);

    httpClient.get('http://localhost:8000/audits').subscribe();

    const req = httpMock.expectOne('http://localhost:8000/audits');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush([]);
  });

  it('should attach Bearer token to API requests when token is present', () => {
    authService.token.set('valid-test-jwt-token');

    httpClient.get('http://localhost:8000/audits').subscribe();

    const req = httpMock.expectOne('http://localhost:8000/audits');
    expect(req.request.headers.has('Authorization')).toBe(true);
    expect(req.request.headers.get('Authorization')).toBe('Bearer valid-test-jwt-token');
    req.flush([]);
  });

  it('should not attach Authorization header to external third-party requests', () => {
    authService.token.set('valid-test-jwt-token');

    httpClient.get('https://external-service.example.com/data').subscribe();

    const req = httpMock.expectOne('https://external-service.example.com/data');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('should clear session and redirect to /login on 401 Unauthorized', () => {
    authService.token.set('expired-jwt-token');
    const clearSpy = vi.spyOn(authService, 'clearSession');
    const navSpy = vi.spyOn(router, 'navigate');

    // Mock router URL as a protected page
    Object.defineProperty(router, 'url', { value: '/audits/test-123', configurable: true });

    httpClient.get('http://localhost:8000/audits/test-123').subscribe({
      next: () => {},
      error: (err) => {
        expect(err.status).toBe(401);
      }
    });

    const req = httpMock.expectOne('http://localhost:8000/audits/test-123');
    req.flush({ detail: 'Token has expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(clearSpy).toHaveBeenCalled();
    expect(navSpy).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/audits/test-123' }
    });
  });

  it('should not redirect if 401 occurs while already on /login', () => {
    const navSpy = vi.spyOn(router, 'navigate');
    Object.defineProperty(router, 'url', { value: '/login', configurable: true });

    httpClient.post('http://localhost:8000/auth/login', { email: 'test@example.com', password: 'wrong' }).subscribe({
      next: () => {},
      error: () => {}
    });

    const req = httpMock.expectOne('http://localhost:8000/auth/login');
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });

    expect(navSpy).not.toHaveBeenCalled();
  });

  it('should NOT log out or redirect on 403 Forbidden', () => {
    authService.token.set('valid-user-token');
    const clearSpy = vi.spyOn(authService, 'clearSession');
    const navSpy = vi.spyOn(router, 'navigate');

    httpClient.get('http://localhost:8000/api/evaluations/runs').subscribe({
      next: () => {},
      error: (err) => {
        expect(err.status).toBe(403);
      }
    });

    const req = httpMock.expectOne('http://localhost:8000/api/evaluations/runs');
    req.flush({ detail: 'Admin privileges required' }, { status: 403, statusText: 'Forbidden' });

    expect(clearSpy).not.toHaveBeenCalled();
    expect(navSpy).not.toHaveBeenCalled();
  });
});
