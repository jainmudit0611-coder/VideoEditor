import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { EvaluationsDashboardComponent } from './evaluations-dashboard.component';
import { EvaluationService } from '../../../../core/services/evaluation.service';
import type { EvaluationRun } from '../../../../core/models/evaluation.model';

describe('EvaluationsDashboardComponent', () => {
  let component: EvaluationsDashboardComponent;
  let fixture: ComponentFixture<EvaluationsDashboardComponent>;
  let evalServiceMock: any;

  const mockRuns: EvaluationRun[] = [
    {
      id: 'eval-run-001',
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
      duration_ms: 6700,
      metrics: {
        finding_precision: 1.0,
        finding_recall: 1.0,
        finding_f1: 1.0,
        evidence_support_rate: 1.0,
        unsupported_finding_rate: 0.0,
        citation_presence_rate: 1.0,
        schema_validity_rate: 1.0,
        verifier_agreement_rate: 1.0
      },
      discrepancies: []
    }
  ];

  beforeEach(async () => {
    evalServiceMock = {
      listRuns: vi.fn().mockReturnValue(of(mockRuns)),
      createRun: vi.fn().mockReturnValue(of({ id: 'eval-new', run_name: 'New Run', status: 'QUEUED', message: 'Queued' })),
      pollRun: vi.fn().mockReturnValue(of(mockRuns[0])),
      compareRuns: vi.fn().mockReturnValue(of({ runs: [], metrics: [], differences: [] }))
    };

    await TestBed.configureTestingModule({
      imports: [EvaluationsDashboardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: EvaluationService, useValue: evalServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EvaluationsDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and load historical runs', () => {
    expect(component).toBeTruthy();
    expect(component.runs.length).toBe(1);
    expect(component.latestRun).toBeTruthy();
    expect(component.latestRun?.run_name).toBe('Benchmark Run 1');
  });

  it('should render dataset banner with scientific disclaimer', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Dataset v1 • MANUALLY_CURATED • 6 cases');
    expect(compiled.textContent).toContain('Methodology & Dataset Scope:');
    expect(compiled.textContent).toContain('should not be interpreted as population-wide production accuracy');
  });

  it('should render primary metric cards for latest run', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Finding Precision');
    expect(compiled.textContent).toContain('100%');
    expect(compiled.textContent).toContain('Evidence Grounding');
    expect(compiled.textContent).toContain('Schema Validity');
  });

  it('should toggle run selection for comparison', () => {
    expect(component.selectedRunIds.size).toBe(0);
    component.toggleRunSelection('run-1');
    expect(component.selectedRunIds.has('run-1')).toBe(true);
    component.toggleRunSelection('run-1');
    expect(component.selectedRunIds.has('run-1')).toBe(false);
  });
});
