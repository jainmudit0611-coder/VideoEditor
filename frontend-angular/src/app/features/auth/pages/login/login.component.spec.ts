import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';
import { signal } from '@angular/core';
import { LoginComponent } from './login.component';
import { AuthService } from '../../../../core/services/auth.service';
import type { User } from '../../../../core/models/auth.model';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let authServiceSpy: any;
  let router: Router;

  const mockUser: User = {
    id: 'user-1',
    email: 'user@example.com',
    display_name: 'Test Officer',
    role: 'USER',
    is_active: true
  };

  beforeEach(async () => {
    authServiceSpy = {
      login: vi.fn(),
      isLoading: signal(false)
    };

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParams: {}
            }
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create login component', () => {
    expect(component).toBeTruthy();
  });

  it('should reject empty fields with validation error', () => {
    component.email = '';
    component.password = '';
    component.onSubmit();

    expect(component.errorMessage()).toBe('Please enter both email and password.');
    expect(authServiceSpy.login).not.toHaveBeenCalled();
  });

  it('should call authService.login and navigate to dashboard on success', () => {
    authServiceSpy.login.mockReturnValue(of(mockUser));
    const navSpy = vi.spyOn(router, 'navigateByUrl');

    component.email = 'user@example.com';
    component.password = 'password123';
    component.onSubmit();

    expect(authServiceSpy.login).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'password123'
    });
    expect(navSpy).toHaveBeenCalledWith('/dashboard');
  });

  it('should display error message on login failure', () => {
    authServiceSpy.login.mockReturnValue(throwError(() => ({
      status: 401,
      error: { detail: 'Incorrect email or password' }
    })));

    component.email = 'user@example.com';
    component.password = 'wrongpassword';
    component.onSubmit();

    expect(component.errorMessage()).toBe('Incorrect email or password');
  });

  it('should navigate to returnUrl from query params on success', () => {
    const route = TestBed.inject(ActivatedRoute);
    (route.snapshot as any).queryParams = { returnUrl: '/audits/target-123' };

    authServiceSpy.login.mockReturnValue(of(mockUser));
    const navSpy = vi.spyOn(router, 'navigateByUrl');

    component.email = 'user@example.com';
    component.password = 'password123';
    component.onSubmit();

    expect(navSpy).toHaveBeenCalledWith('/audits/target-123');
  });

  it('should disable submit button when loading', () => {
    authServiceSpy.isLoading.set(true);
    fixture.detectChanges();

    const submitBtn: HTMLButtonElement = fixture.nativeElement.querySelector('button[type="submit"]');
    expect(submitBtn.disabled).toBe(true);
  });
});
