# Tasks: Webapp Frontend

**Input**: Design documents from `/specs/003-webapp-frontend/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `webapp/` directory at repository root
- Paths shown assume webapp/ structure from plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create webapp/ directory structure per implementation plan
- [X] T002 Initialize Next.js 14 project with TypeScript and App Router
- [X] T003 Configure Tailwind CSS with custom configuration
- [X] T004 Install and configure shadcn/ui components
- [ ] T005 [P] Initialize ESLint and Prettier configuration
- [ ] T006 [P] Set up Husky pre-commit hooks
- [X] T007 Configure TypeScript strict mode
- [ ] T008 [P] Set up Jest and React Testing Library

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 Create app/ directory structure with layout.tsx and page.tsx
- [X] T010 [P] Set up components/ directory with ui/ subdirectory
- [X] T011 [P] Create lib/ directory for utilities and API client
- [X] T012 [P] Set up types/ directory for TypeScript definitions from data-model.md
- [X] T013 [P] Create hooks/ directory for custom React hooks
- [X] T014 Configure public/ directory for static assets
- [ ] T015 Create environment configuration with .env.local template
- [X] T016 Install React Query (TanStack Query) for state management
- [X] T017 [P] Create API client configuration for workspaces and search APIs
- [ ] T018 [P] Set up error handling utilities and global error boundaries
- [X] T019 Configure build and development scripts in package.json

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Dashboard Overview (Priority: P1) 🎯 MVP

**Goal**: As a user, I want to view a dashboard overview of all workspaces so that I can get a quick understanding of the system status.

**Independent Test**: Navigate to the dashboard page and verify that workspace cards are displayed with key metrics, and the interface is responsive.

### Implementation for User Story 1

- [X] T020 [P] [US1] Create Workspace interface types in webapp/types/workspace.ts
- [X] T021 [P] [US1] Create API hooks for workspaces endpoint in webapp/lib/api/workspaces.ts
- [X] T022 [P] [US1] Implement WorkspaceCard component in webapp/components/dashboard/WorkspaceCard.tsx
- [X] T023 [P] [US1] Implement MetricCards component in webapp/components/dashboard/MetricCards.tsx
- [X] T024 [P] [US1] Create AppShell layout component in webapp/components/layout/AppShell.tsx
- [X] T025 [P] [US1] Implement Sidebar navigation component in webapp/components/layout/Sidebar.tsx
- [X] T026 [P] [US1] Create Header component with search bar in webapp/components/layout/Header.tsx
- [X] T027 [US1] Implement dashboard page in webapp/app/page.tsx using workspace data
- [X] T028 [US1] Add responsive grid layout for workspace cards
- [X] T029 [US1] Implement loading states with skeleton components

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Semantic Search (Priority: P1)

**Goal**: As a user, I want to perform semantic searches across workspaces using natural language so that I can find relevant information quickly.

**Independent Test**: Enter a search query and verify that relevant results are displayed with proper highlighting and metadata.

### Implementation for User Story 2

- [ ] T030 [P] [US2] Create SearchResult and SearchQuery interface types in webapp/types/search.ts
- [ ] T031 [P] [US2] Create API hooks for search endpoint in webapp/lib/api/search.ts
- [ ] T032 [P] [US2] Implement SearchBar component in webapp/components/search/SearchBar.tsx
- [ ] T033 [P] [US2] Create SearchResults component in webapp/components/search/SearchResults.tsx
- [ ] T034 [P] [US2] Implement SearchFilters component in webapp/components/search/SearchFilters.tsx
- [ ] T035 [US2] Create search page in webapp/app/search/page.tsx
- [ ] T036 [US2] Add search functionality to dashboard header
- [ ] T037 [US2] Implement result highlighting and preview
- [ ] T038 [US2] Add pagination for search results

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Workspace Details (Priority: P2)

**Goal**: As a user, I want to view detailed information about a specific workspace so that I can understand its contents and activity.

**Independent Test**: Click on a workspace card and verify that detailed profile information, analytics, and activity feed are displayed.

### Implementation for User Story 3

- [ ] T039 [P] [US3] Create WorkspaceProfile interface types in webapp/types/workspace.ts
- [ ] T040 [P] [US3] Create API hooks for workspace details endpoint in webapp/lib/api/workspaces.ts
- [ ] T041 [P] [US3] Implement ProfileCard component in webapp/components/workspace/ProfileCard.tsx
- [ ] T042 [P] [US3] Create ToolChart component using Recharts in webapp/components/workspace/ToolChart.tsx
- [ ] T043 [P] [US3] Implement ArtifactList component in webapp/components/workspace/ArtifactList.tsx
- [ ] T044 [P] [US3] Create InsightPanel component in webapp/components/workspace/InsightPanel.tsx
- [ ] T045 [US3] Implement workspace detail page in webapp/app/workspace/[id]/page.tsx
- [ ] T046 [US3] Add navigation from dashboard to workspace details
- [ ] T047 [US3] Implement responsive layout for workspace details

**Checkpoint**: User Story 3 should now be independently functional

---

## Phase 6: User Story 4 - Artifact Browsing (Priority: P2)

**Goal**: As a user, I want to browse and filter workspace artifacts so that I can explore specific files and code.

**Independent Test**: Navigate to workspace details and verify that artifacts can be filtered by type, sorted, and viewed with syntax highlighting.

### Implementation for User Story 4

- [ ] T048 [P] [US4] Create ArtifactMetadata interface types in webapp/types/artifact.ts
- [ ] T049 [P] [US4] Implement DataTable component in webapp/components/ui/DataTable.tsx
- [ ] T050 [P] [US4] Create ArtifactViewer component with syntax highlighting in webapp/components/workspace/ArtifactViewer.tsx
- [ ] T051 [P] [US4] Implement filter controls in webapp/components/workspace/ArtifactFilters.tsx
- [ ] T052 [US4] Add artifact browsing to workspace detail page
- [ ] T053 [US4] Implement sorting and pagination for artifacts
- [ ] T054 [US4] Add file type icons and metadata display

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T055 [P] Implement theme system with light/dark mode toggle
- [ ] T056 [P] Add accessibility features (ARIA labels, keyboard navigation)
- [ ] T057 Configure Storybook for component development
- [ ] T058 [P] Implement error pages (404, 500) in webapp/app/
- [ ] T059 [P] Add loading states and skeleton components throughout
- [ ] T060 Optimize bundle size and implement code splitting
- [ ] T061 [P] Add performance monitoring and analytics
- [ ] T062 Create comprehensive README for webapp development
- [ ] T063 Run quickstart.md validation and update documentation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Depends on US3 for workspace context

### Within Each User Story

- Types and API hooks before components
- Components before pages
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Types and API hooks within a story marked [P] can run in parallel
- Components within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Terminal 1: Types and API
npm run dev  # Start dev server
# Implement T020, T021 in parallel

# Terminal 2: Components  
# Implement T022, T023, T024, T025, T026 in parallel

# Terminal 3: Page integration
# Implement T027, T028, T029 after components ready
```

---

## Implementation Strategy

**MVP Scope**: User Stories 1 & 2 (Dashboard + Search) - Core functionality for workspace overview and discovery

**Incremental Delivery**:
1. **Week 1**: Setup + Foundation (Phases 1-2) - Get development environment ready
2. **Week 2**: US1 Dashboard (Phase 3) - Basic workspace overview
3. **Week 3**: US2 Search (Phase 4) - Add semantic search capability  
4. **Week 4**: US3 & US4 Details (Phases 5-6) - Enhanced workspace exploration
5. **Week 5**: Polish (Phase 7) - Performance, accessibility, documentation

**Success Metrics**:
- Lighthouse performance score > 90
- WCAG 2.1 AA accessibility compliance
- All user stories independently testable
- Responsive across desktop/tablet/mobile
- Fast loading times (< 3s initial load)

## Phase 10: Documentation & Launch (Priority: P3)

**Goal**: Complete documentation and prepare for launch.

- [ ] T055 [P3] Create user documentation and guides
- [ ] T056 [P3] Add component documentation with Storybook
- [ ] T057 [P3] Write API documentation for frontend integration
- [ ] T058 [P3] Create deployment and maintenance guides
- [ ] T059 [P3] Add contribution guidelines for future development
- [ ] T060 [P3] Prepare launch checklist and go-live plan