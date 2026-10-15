import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';
import { environment } from '../../../environments/environment';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = authService.getAccessToken();

  // Only attach authorization headers to internal backend API requests
  const isApiRequest = req.url.startsWith(environment.apiBaseUrl) || req.url.startsWith('/');

  let authReq = req;
  if (token && isApiRequest) {
    authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        // Clear invalid/expired session
        authService.clearSession();

        // Redirect to /login if not already on an authentication route
        const currentUrl = router.url;
        if (!currentUrl.includes('/login') && !currentUrl.includes('/register')) {
          router.navigate(['/login'], {
            queryParams: { returnUrl: currentUrl }
          });
        }
      }
      return throwError(() => error);
    })
  );
};
