# Brand Guardian AI — Angular Frontend Dashboard

The Angular implementation of the **Brand Guardian AI** (`VIDEO_AUDIT_PROJ`) video compliance intelligence dashboard.

Migrated from React to **Angular 21** using standalone components, Angular Router, Signals, RxJS, and Tailwind CSS.

---

## Technical Stack

* **Framework**: Angular 21 (Standalone Components)
* **Language**: TypeScript 5.9+ (Strict Mode)
* **Styling**: Tailwind CSS v4 + PostCSS with Enterprise Glassmorphism Theme
* **HTTP & Polling**: Angular `HttpClient` + RxJS (`timer`, `switchMap`, `takeWhile`)
* **State Management**: Angular Signals & RxJS Observables
* **Testing**: Vitest with Angular `@angular/build:unit-test`

---

## Features

1. **Dashboard (`/dashboard`)**:
   - Aggregate metric KPI cards: Total Audits, Active Workers Processing, Completed Audits, Issues Found.
   - Live system status indicators (API, DB, Redis queue).
   - Recent Audits table with interactive detail view links and real-time status badges.

2. **New Audit Form (`/audits/new`)**:
   - Reactive Forms with URL protocol and format validation.
   - Asynchronous job submission to `POST /audits` (returns 202 Accepted).
   - Instant routing to live audit lifecycle tracking.

3. **Audit Details (`/audits/:id`)**:
   - Real-time status polling using RxJS (2.5s interval) until terminal state (`COMPLETED`, `FAILED`, `CANCELLED`).
   - Interactive stage-by-stage workflow timeline (`WorkflowProgressComponent`).
   - Job cancellation (`POST /audits/:id/cancel`) for active queued or processing jobs.
   - Degraded mode notification banner (`DegradedModeBannerComponent`).

4. **Compliance Report & Deliverables**:
   - Executive Summary Markdown report box.
   - Evidence Verification & Critic Agent summary card.
   - Compliance Findings list categorized by `PASS`, `WARNING`, and `FAIL` severities.
   - Multimodal Evidence Explorer tabbed by **Transcript**, **OCR**, and **Visual** streams with timestamp anchoring and confidence scores.
   - Policy / RAG Citations retrieved from Azure AI Search / Policy Vector DB.
   - Agent execution metadata card (Iterations, Observations, Policy matches).
   - Pipeline Stage Latencies performance table.
   - Browser print stylesheet (`@media print`) for compliance auditors.

---

## Environment Configuration

Configure API endpoints in `src/environments/`:
- Development: `src/environments/environment.development.ts`
- Production: `src/environments/environment.ts`

```typescript
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000'
};
```

---

## Installation & Commands

### Install Dependencies

```bash
cd frontend-angular
npm install --legacy-peer-deps
```

### Start Local Development Server

```bash
npm start
# or: ng serve
```

Default local address: `http://localhost:4200`

### Run Unit Tests

```bash
npm test -- --watch=false
```

### Build Production Bundle

```bash
npm run build
```

Production output is compiled to `dist/frontend-angular/`.

---

## Project Structure

```text
frontend-angular/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── models/           # Audit & API TypeScript interfaces
│   │   │   └── services/         # ApiService, AuditService, HealthService
│   │   ├── shared/
│   │   │   ├── components/       # StatusBadge, DegradedModeBanner, LoadingSkeleton, ErrorAlert
│   │   │   └── utils/            # Status and formatting helper utilities
│   │   ├── layout/
│   │   │   ├── header/           # System readiness header
│   │   │   ├── sidebar/          # Architecture & navigation sidebar
│   │   │   └── layout/           # Main application layout wrapper
│   │   ├── features/
│   │   │   └── audits/
│   │   │       ├── pages/        # DashboardComponent, NewAuditComponent, AuditDetailsComponent, NotFoundComponent
│   │   │       └── components/   # WorkflowProgress, StageLatency, AgentActivity, EvidenceExplorer,
│   │   │                         # FindingsList, VerifierCard, PolicyCitations, ReportViewer
│   │   ├── app.routes.ts         # Application routing configuration
│   │   ├── app.config.ts         # Application provider configuration
│   │   └── app.ts                # Root standalone component
│   ├── environments/             # Environment configuration (dev & prod)
│   ├── styles.css                # Global Tailwind CSS and glassmorphism styling
│   └── index.html                # HTML entry point with fonts & metadata
├── angular.json                  # Angular CLI configuration
├── package.json                  # Node dependencies and scripts
└── tsconfig.json                 # TypeScript compiler configuration
```
