import { Routes } from '@angular/router';
import { DashboardComponent } from './features/audits/pages/dashboard/dashboard.component';
import { NewAuditComponent } from './features/audits/pages/new-audit/new-audit.component';
import { AuditDetailsComponent } from './features/audits/pages/audit-details/audit-details.component';
import { EvaluationsDashboardComponent } from './features/evaluations/pages/evaluations-dashboard/evaluations-dashboard.component';
import { EvaluationDetailsComponent } from './features/evaluations/pages/evaluation-details/evaluation-details.component';
import { NotFoundComponent } from './features/audits/pages/not-found/not-found.component';
import { LoginComponent } from './features/auth/pages/login/login.component';
import { RegisterComponent } from './features/auth/pages/register/register.component';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'audits/new', component: NewAuditComponent, canActivate: [authGuard] },
  { path: 'audits/:id', component: AuditDetailsComponent, canActivate: [authGuard] },
  { path: 'evaluations', component: EvaluationsDashboardComponent, canActivate: [authGuard] },
  { path: 'evaluations/:id', component: EvaluationDetailsComponent, canActivate: [authGuard] },
  { path: '**', component: NotFoundComponent }
];


