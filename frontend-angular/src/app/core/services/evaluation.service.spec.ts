import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { EvaluationService } from './evaluation.service';
import type { EvaluationRun, CreateEvaluationRunResponse, EvaluationComparison } from '../models/evaluation.model';

describe('EvaluationService', () => {
  let service: EvaluationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        EvaluationService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(EvaluationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should trigger evaluation run (POST /api/evaluations/runs)', () => {
    const dummyResponse: CreateEvaluationRunResponse = {
      id: 'eval-run-123',
      run_name: 'Test Run',
      status: 'QUEUED',
      message: 'Evaluation run accepted and queued.'
    };

    service.createRun({ run_name: 'Test Run' }).subscribe(res => {
      expect(res.id).toBe('eval-run-123');
      expect(res.status).toBe('QUEUED');
    });

    const req = httpMock.expectOne('http://localhost:8000/api/evaluations/runs');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ run_name: 'Test Run' });
    req.flush(dummyResponse);
  });

  it('should list evaluation runs (GET /api/evaluations/runs)', () => {
    const dummyRuns: EvaluationRun[] = [
      {
        id: 'eval-1',
        run_name: 'Benchmark Run 1',
        status: 'COMPLETED',
        dataset_version: 'v1',
        dataset_type: 'MANUALLY_CURATED',
        case_count: 6,
        model_name: 'gpt-4o',
        model_provider: 'azure_openai',
        prompt_version: 'v1',
        config_version: 'v1',
        evaluation_version: 'v1',
        metrics: {
          finding_precision: 1.0,
          finding_recall: 1.0,
          finding_f1: 1.0
        }
      }
    ];

    service.listRuns().subscribe(runs => {
      expect(runs.length).toBe(1);
      expect(runs[0].id).toBe('eval-1');
      expect(runs[0].metrics.finding_f1).toBe(1.0);
    });

    const req = httpMock.expectOne('http://localhost:8000/api/evaluations/runs');
    expect(req.request.method).toBe('GET');
    req.flush(dummyRuns);
  });

  it('should get run detail (GET /api/evaluations/runs/:id)', () => {
    const dummyRun: EvaluationRun = {
      id: 'eval-1',
      run_name: 'Benchmark Run 1',
      status: 'COMPLETED',
      dataset_version: 'v1',
      dataset_type: 'MANUALLY_CURATED',
      case_count: 6,
      model_name: 'gpt-4o',
      model_provider: 'azure_openai',
      prompt_version: 'v1',
      config_version: 'v1',
      evaluation_version: 'v1',
      metrics: { finding_f1: 1.0 }
    };

    service.getRun('eval-1').subscribe(run => {
      expect(run.id).toBe('eval-1');
      expect(run.status).toBe('COMPLETED');
    });

    const req = httpMock.expectOne('http://localhost:8000/api/evaluations/runs/eval-1');
    expect(req.request.method).toBe('GET');
    req.flush(dummyRun);
  });

  it('should compare runs (GET /api/evaluations/compare)', () => {
    const dummyComparison: EvaluationComparison = {
      runs: [],
      metrics: [
        {
          metric: 'Finding Precision',
          key: 'finding_precision',
          display_type: '%',
          values: { 'id1': 0.85, 'id2': 0.90 },
          delta: 0.05
        }
      ],
      differences: []
    };

    service.compareRuns(['id1', 'id2']).subscribe(comp => {
      expect(comp.metrics.length).toBe(1);
      expect(comp.metrics[0].delta).toBe(0.05);
    });

    const req = httpMock.expectOne('http://localhost:8000/api/evaluations/compare?run_ids=id1%2Cid2');
    expect(req.request.method).toBe('GET');
    req.flush(dummyComparison);
  });
});
