import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuditService } from './audit.service';
import type { AuditJob } from '../models/audit.model';

describe('AuditService', () => {
  let service: AuditService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AuditService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(AuditService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should create an audit job (POST /audits)', () => {
    const dummyResponse = {
      audit_id: 'test-audit-123',
      status: 'QUEUED' as const,
      video_url: 'https://www.youtube.com/watch?v=test',
      message: 'Audit job enqueued successfully.'
    };

    service.createAudit('https://www.youtube.com/watch?v=test').subscribe(res => {
      expect(res.audit_id).toBe('test-audit-123');
      expect(res.status).toBe('QUEUED');
    });

    const req = httpMock.expectOne('http://localhost:8000/audits');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ video_url: 'https://www.youtube.com/watch?v=test' });
    req.flush(dummyResponse);
  });

  it('should list audit jobs (GET /audits)', () => {
    const dummyJobs: AuditJob[] = [
      {
        audit_id: 'job-1',
        status: 'COMPLETED',
        video_url: 'https://www.youtube.com/watch?v=1',
        created_at: '2026-09-23T10:00:00Z',
        started_at: null,
        completed_at: null,
        progress: 100,
        current_stage: 'COMPLETED',
        iteration_count: 1,
        retry_count: 0
      }
    ];

    service.listAudits(10, 0).subscribe(jobs => {
      expect(jobs.length).toBe(1);
      expect(jobs[0].audit_id).toBe('job-1');
    });

    const req = httpMock.expectOne('http://localhost:8000/audits?limit=10&offset=0');
    expect(req.request.method).toBe('GET');
    req.flush(dummyJobs);
  });

  it('should cancel an audit job (POST /audits/:id/cancel)', () => {
    const dummyCancelRes = {
      audit_id: 'job-cancel-1',
      status: 'CANCELLED' as const,
      message: 'Audit job cancelled successfully.'
    };

    service.cancelAudit('job-cancel-1').subscribe(res => {
      expect(res.status).toBe('CANCELLED');
    });

    const req = httpMock.expectOne('http://localhost:8000/audits/job-cancel-1/cancel');
    expect(req.request.method).toBe('POST');
    req.flush(dummyCancelRes);
  });
});
