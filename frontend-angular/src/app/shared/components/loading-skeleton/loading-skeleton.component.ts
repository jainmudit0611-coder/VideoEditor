import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-4 animate-pulse">
      <div class="h-8 bg-gray-800/60 rounded-md w-1/3"></div>
      @for (item of rowArray; track $index) {
        <div class="h-20 bg-gray-800/40 rounded-lg w-full border border-gray-800"></div>
      }
    </div>
  `
})
export class LoadingSkeletonComponent {
  @Input() rows = 3;

  get rowArray(): number[] {
    return Array(this.rows).fill(0);
  }
}
