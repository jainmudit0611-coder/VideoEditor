import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FindingsListComponent } from './findings-list.component';
import type { ComplianceIssue } from '../../../../core/models/audit.model';

describe('FindingsListComponent', () => {
  let component: FindingsListComponent;
  let fixture: ComponentFixture<FindingsListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FindingsListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(FindingsListComponent);
    component = fixture.componentInstance;
  });

  it('should render empty state when no findings present', () => {
    component.findings = [];
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('No Compliance Violations Detected');
  });

  it('should render finding items with severity and category', () => {
    const mockFindings: ComplianceIssue[] = [
      {
        category: 'FTC Disclosure Missing',
        severity: 'FAIL',
        description: 'No clear sponsorship notice found in video audio or frames.',
        timestamp: '00:15',
        rule_id: 'FTC_16_CFR_255'
      }
    ];

    component.findings = mockFindings;
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('FTC Disclosure Missing');
    expect(text).toContain('FAIL');
    expect(text).toContain('00:15');
    expect(text).toContain('Rule ID: FTC_16_CFR_255');
  });
});
