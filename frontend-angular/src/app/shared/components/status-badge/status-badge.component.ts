import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { AuditStatusType } from '../../../core/models/audit.model';
import { getStatusColorClass } from '../../utils/status.utils';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      class="inline-flex items-center font-medium rounded-md border shadow-xs transition-colors"
      [ngClass]="[colors.badge, sizeClass, customClass]"
    >
      <span class="w-1.5 h-1.5 rounded-full" [ngClass]="colors.dot"></span>
      <span>{{ status }}</span>
    </span>
  `
})
export class StatusBadgeComponent {
  @Input({ required: true }) status: AuditStatusType | string = 'QUEUED';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() customClass = '';

  get colors() {
    return getStatusColorClass(this.status);
  }

  get sizeClass(): string {
    switch (this.size) {
      case 'sm':
        return 'px-2 py-0.5 text-xs gap-1.5';
      case 'lg':
        return 'px-3 py-1.5 text-sm gap-2';
      default:
        return 'px-2.5 py-1 text-xs gap-2';
    }
  }
}
