import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { NewAuditComponent } from './new-audit.component';
import { AuditService } from '../../../../core/services/audit.service';
import type { CreateAuditResponse } from '../../../../core/models/api.model';

describe('NewAuditComponent', () => {
  let component: NewAuditComponent;
  let fixture: ComponentFixture<NewAuditComponent>;
  let auditServiceSpy: any;
  let router: Router;

  beforeEach(async () => {
    auditServiceSpy = {
      createAudit: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [NewAuditComponent],
      providers: [
        provideRouter([]),
        { provide: AuditService, useValue: auditServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(NewAuditComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should reject empty URL on submit', () => {
    component.auditForm.patchValue({ videoUrl: '' });
    component.onSubmit();
    expect(component.errorMessage()).toBe('Please enter a target video URL.');
    expect(auditServiceSpy.createAudit).not.toHaveBeenCalled();
  });

  it('should reject invalid URL protocol', () => {
    component.auditForm.patchValue({ videoUrl: 'ftp://example.com/video.mp4' });
    component.onSubmit();
    expect(component.errorMessage()).toContain('Please enter a valid HTTP or HTTPS video URL');
    expect(auditServiceSpy.createAudit).not.toHaveBeenCalled();
  });

  it('should submit valid video URL and navigate to /audits/:id', () => {
    const validUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
    const mockResponse: CreateAuditResponse = {
      audit_id: 'mock-audit-999',
      status: 'QUEUED',
      video_url: validUrl,
      message: 'Enqueued'
    };
    auditServiceSpy.createAudit.mockReturnValue(of(mockResponse));
    const navigateSpy = vi.spyOn(router, 'navigate');

    component.auditForm.patchValue({ videoUrl: validUrl });
    component.onSubmit();

    expect(auditServiceSpy.createAudit).toHaveBeenCalledWith(validUrl);
    expect(navigateSpy).toHaveBeenCalledWith(['/audits', 'mock-audit-999']);
  });
});
