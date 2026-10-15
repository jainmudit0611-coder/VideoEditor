import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';
import { authGuard } from './auth.guard';
import { adminGuard } from './admin.guard';
import { AuthService } from '../services/auth.service';
import type { User } from '../models/auth.model';

describe('Auth Guards', () => {
  let authServiceSpy: {
    getAccessToken: ReturnType<typeof vi.fn>;
    currentUser: ReturnType<typeof vi.fn>;
  };
  let router: Router;

  const dummyRoute = {} as ActivatedRouteSnapshot;
  const dummyState = { url: '/audits/test-456' } as RouterStateSnapshot;

  beforeEach(() => {
    authServiceSpy = {
      getAccessToken: vi.fn(),
      currentUser: vi.fn()
    };

    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceSpy }
      ]
    });

    router = TestBed.inject(Router);
  });

  describe('authGuard', () => {
    it('should allow access when user has an access token', () => {
      authServiceSpy.getAccessToken.mockReturnValue('valid-token-abc');

      const result = TestBed.runInInjectionContext(() => authGuard(dummyRoute, dummyState));
      expect(result).toBe(true);
    });

    it('should redirect unauthenticated users to /login preserving returnUrl', () => {
      authServiceSpy.getAccessToken.mockReturnValue(null);

      const result = TestBed.runInInjectionContext(() => authGuard(dummyRoute, dummyState));
      expect(result instanceof UrlTree).toBe(true);
      const urlTree = result as UrlTree;
      expect(router.serializeUrl(urlTree)).toBe('/login?returnUrl=%2Faudits%2Ftest-456');
    });
  });

  describe('adminGuard', () => {
    it('should allow access when user has ADMIN role', () => {
      const adminUser: User = {
        id: 'admin-1',
        email: 'admin@brandguardian.ai',
        display_name: 'Admin User',
        role: 'ADMIN',
        is_active: true
      };
      authServiceSpy.currentUser.mockReturnValue(adminUser);

      const result = TestBed.runInInjectionContext(() => adminGuard(dummyRoute, dummyState));
      expect(result).toBe(true);
    });

    it('should redirect non-admin users to /dashboard', () => {
      const normalUser: User = {
        id: 'user-1',
        email: 'user@brandguardian.ai',
        display_name: 'Regular User',
        role: 'USER',
        is_active: true
      };
      authServiceSpy.currentUser.mockReturnValue(normalUser);

      const result = TestBed.runInInjectionContext(() => adminGuard(dummyRoute, dummyState));
      expect(result instanceof UrlTree).toBe(true);
      const urlTree = result as UrlTree;
      expect(router.serializeUrl(urlTree)).toBe('/dashboard');
    });

    it('should redirect when user is null to /dashboard', () => {
      authServiceSpy.currentUser.mockReturnValue(null);

      const result = TestBed.runInInjectionContext(() => adminGuard(dummyRoute, dummyState));
      expect(result instanceof UrlTree).toBe(true);
      const urlTree = result as UrlTree;
      expect(router.serializeUrl(urlTree)).toBe('/dashboard');
    });
  });
});
