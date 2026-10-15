import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.getAccessToken()) {
    return true;
  }

  // Preserve returnUrl so the user can be redirected after successful sign-in
  return router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url }
  });
};
