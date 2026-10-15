import { ComponentFixture, TestBed } from '@angular/core/testing';
import { WorkflowProgressComponent } from './workflow-progress.component';
import type { AuditJob } from '../../../../core/models/audit.model';

describe('WorkflowProgressComponent', () => {
  let component: WorkflowProgressComponent;
  let fixture: ComponentFixture<WorkflowProgressComponent>;

  const mockJob: AuditJob = {
    audit_id: 'test-progress-1',
    status: 'PROCESSING',
    video_url: 'https://youtube.com/watch?v=1',
    created_at: '2026-09-23T10:00:00Z',
    started_at: null,
    completed_at: null,
    progress: 45,
    current_stage: 'AUDITING',
    iteration_count: 1,
    retry_count: 0
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkflowProgressComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(WorkflowProgressComponent);
    component = fixture.componentInstance;
    component.job = mockJob;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display progress percentage and current stage', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('45%');
    expect(text).toContain('AUDITING');
  });

  it('should identify completed and active stages', () => {
    const stages = component.stages;
    // Stage 0 (ingestion) should be completed when current_stage is AUDITING
    expect(component.getStageStatus(stages[0], 0)).toBe('completed');
    // Stage 3 (auditing) should be active
    expect(component.getStageStatus(stages[3], 3)).toBe('active');
    // Stage 5 (report) should be upcoming
    expect(component.getStageStatus(stages[5], 5)).toBe('upcoming');
  });
});
