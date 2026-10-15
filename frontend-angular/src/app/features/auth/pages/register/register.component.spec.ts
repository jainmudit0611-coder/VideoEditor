import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { signal } from '@angular/core';
import { RegisterComponent } from './register.component';
import { AuthService } from '../../../../core/services/auth.service';
import type { User } from '../../../../core/models/auth.model';

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let fixture: ComponentFixture<RegisterComponent>;
  let authServiceSpy: any;
  let router: Router;

  const mockUser: User = {
    id: 'user-new',
    email: 'newofficer@brandguardian.ai',
    display_name: 'Compliance Officer',
    role: 'USER',
    is_active: true
  };

  beforeEach(async () => {
    authServiceSpy = {
      register: vi.fn(),
      login: vi.fn(),
      isLoading: signal(false)
    };

    await TestBed.configureTestingModule({
      imports: [RegisterComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(RegisterComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create register component', () => {
    expect(component).toBeTruthy();
  });

  it('should reject submission when required fields are empty', () => {
    component.displayName = '';
    component.email = '';
    component.password = '';
    component.confirmPassword = '';
    component.onSubmit();

    expect(component.errorMessage()).toBe('All fields are required.');
    expect(authServiceSpy.register).not.toHaveBeenCalled();
  });

  it('should reject password less than 6 characters', () => {
    component.displayName = 'Alice';
    component.email = 'alice@example.com';
    component.password = '12345';
    component.confirmPassword = '12345';
    component.onSubmit();

    expect(component.errorMessage()).toBe('Password must be at least 6 characters long.');
    expect(authServiceSpy.register).not.toHaveBeenCalled();
  });

  it('should reject when passwords do not match', () => {
    component.displayName = 'Alice';
    component.email = 'alice@example.com';
    component.password = 'password123';
    component.confirmPassword = 'password456';
    component.onSubmit();

    expect(component.errorMessage()).toBe('Passwords do not match.');
    expect(authServiceSpy.register).not.toHaveBeenCalled();
  });

  it('should submit registration, auto-authenticate and navigate to dashboard on success', () => {
    authServiceSpy.register.mockReturnValue(of(mockUser));
    authServiceSpy.login.mockReturnValue(of(mockUser));
    const navSpy = vi.spyOn(router, 'navigate');

    component.displayName = 'Alice Compliance';
    component.email = 'alice@example.com';
    component.password = 'securePass123';
    component.confirmPassword = 'securePass123';
    component.onSubmit();

    expect(authServiceSpy.register).toHaveBeenCalledWith({
      display_name: 'Alice Compliance',
      email: 'alice@example.com',
      password: 'securePass123'
    });
    expect(authServiceSpy.login).toHaveBeenCalledWith({
      email: 'alice@example.com',
      password: 'securePass123'
    });
    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('should display error message on 409 conflict (duplicate email)', () => {
    authServiceSpy.register.mockReturnValue(throwError(() => ({
      status: 409,
      error: { detail: 'Email already registered' }
    })));

    component.displayName = 'Alice';
    component.email = 'existing@example.com';
    component.password = 'securePass123';
    component.confirmPassword = 'securePass123';
    component.onSubmit();

    expect(component.errorMessage()).toBe('Email already registered');
  });
});
