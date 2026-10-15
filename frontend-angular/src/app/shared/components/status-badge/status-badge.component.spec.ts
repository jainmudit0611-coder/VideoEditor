import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StatusBadgeComponent } from './status-badge.component';

describe('StatusBadgeComponent', () => {
  let component: StatusBadgeComponent;
  let fixture: ComponentFixture<StatusBadgeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatusBadgeComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(StatusBadgeComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render the status text', () => {
    component.status = 'COMPLETED';
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('COMPLETED');
  });

  it('should apply emerald colors for COMPLETED status', () => {
    component.status = 'COMPLETED';
    const colors = component.colors;
    expect(colors.badge).toContain('emerald');
  });

  it('should apply rose colors for FAILED status', () => {
    component.status = 'FAILED';
    const colors = component.colors;
    expect(colors.badge).toContain('rose');
  });
});
