import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export class ApiRequestError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.detail = detail;
  }
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiBaseUrl;

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = `HTTP Error ${error.status}: ${error.statusText}`;
    let detail: string | undefined;

    if (error.error && typeof error.error === 'object') {
      detail = error.error.detail || error.error.message;
      if (detail) {
        errorMessage = detail;
      }
    }

    if (error.status === 503) {
      errorMessage = detail || 'The audit service is temporarily unavailable. Please try again shortly.';
    } else if (error.status === 404) {
      errorMessage = detail || 'The requested audit resource was not found.';
    } else if (error.status === 400) {
      errorMessage = detail || 'Invalid request parameters. Please verify input.';
    } else if (error.status === 0) {
      errorMessage = 'Unable to connect to Brand Guardian AI. Please check that the API server is running at ' + this.baseUrl;
    }

    return throwError(() => new ApiRequestError(error.status, errorMessage, detail));
  }

  get<T>(endpoint: string, headers?: HttpHeaders): Observable<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    return this.http.get<T>(url, { headers }).pipe(
      catchError(err => this.handleError(err))
    );
  }

  post<T>(endpoint: string, body: any, headers?: HttpHeaders): Observable<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    return this.http.post<T>(url, body, { headers }).pipe(
      catchError(err => this.handleError(err))
    );
  }
}
