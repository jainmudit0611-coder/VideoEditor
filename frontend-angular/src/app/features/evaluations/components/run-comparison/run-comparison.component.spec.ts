import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RunComparisonComponent } from './run-comparison.component';
import type { EvaluationComparison } from '../../../../core/models/evaluation.model';

describe('RunComparisonComponent', () => {
  let component: RunComparisonComponent;
  let fixture: ComponentFixture<RunComparisonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RunComparisonComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(RunComparisonComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should correctly format percentage and float metrics', () => {
    expect(component.formatMetricValue(0.854, '%')).toBe('85.4%');
    expect(component.formatMetricValue(0.854, 'float')).toBe('0.85');
    expect(component.formatMetricValue(null, '%')).toBe('N/A');
  });

  it('should format delta differences with appropriate sign', () => {
    expect(component.formatDelta(0.05, '%')).toBe('+5.0%');
    expect(component.formatDelta(-0.03, '%')).toBe('-3.0%');
    expect(component.formatDelta(null, '%')).toBe('—');
  });

  it('should render comparison table when visible is true', () => {
    const dummyComparison: EvaluationComparison = {
      runs: [
        {
          id: 'run-1',
          run_name: 'Run A',
          status: 'COMPLETED',
          model_name: 'gpt-4o',
          model_provider: 'azure_openai',
          prompt_version: 'v1',
          config_version: 'v1',
          dataset_version: 'v1',
          dataset_type: 'MANUALLY_CURATED',
          case_count: 6
        },
        {
          id: 'run-2',
          run_name: 'Run B',
          status: 'COMPLETED',
          model_name: 'gpt-4o-mini',
          model_provider: 'azure_openai',
          prompt_version: 'v1',
          config_version: 'v1',
          dataset_version: 'v1',
          dataset_type: 'MANUALLY_CURATED',
          case_count: 6
        }
      ],
      metrics: [
        {
          metric: 'Finding F1 Score',
          key: 'finding_f1',
          display_type: 'float',
          values: { 'run-1': 0.85, 'run-2': 0.90 },
          delta: 0.05
        }
      ],
      differences: [
        {
          field: 'Model Name',
          values: { 'run-1': 'gpt-4o', 'run-2': 'gpt-4o-mini' },
          has_difference: true
        }
      ]
    };

    component.comparison = dummyComparison;
    component.visible = true;
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Evaluation Run Comparison');
    expect(compiled.textContent).toContain('Run A');
    expect(compiled.textContent).toContain('Run B');
    expect(compiled.textContent).toContain('Finding F1 Score');
    expect(compiled.textContent).toContain('+0.05');
  });
});
