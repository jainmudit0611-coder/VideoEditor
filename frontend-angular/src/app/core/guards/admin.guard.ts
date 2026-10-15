import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const user = authService.currentUser();
  if (user && user.role === 'ADMIN') {
    return true;
  }

  // Non-admins are redirected back to the dashboard
  return router.createUrlTree(['/dashboard']);
};
