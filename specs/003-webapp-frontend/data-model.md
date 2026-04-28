# Webapp Frontend Data Models

## Overview

This document defines the data models and API contracts used by the webapp frontend. These models ensure type safety and consistency between the frontend and backend APIs.

## Core Data Models

### Workspace

```typescript
interface Workspace {
  id: string
  name: string
  description?: string
  artifact_count: number
  last_updated: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
}
```

### Workspace Profile

```typescript
interface WorkspaceProfile {
  workspace_id: string
  artifact_count: number
  top_tools: ToolUsage[]
  top_topics: TopicRelevance[]
  collaboration_patterns: CollaborationMetrics
  last_updated?: string
  file_types: Record<string, number>
  code_metrics: CodeMetrics
}

interface ToolUsage {
  tool: string
  count: number
}

interface TopicRelevance {
  topic: string
  relevance: number
}

interface CollaborationMetrics {
  total_artifacts: number
  notebooks_count: number
  scripts_count: number
  avg_file_size: number
}

interface CodeMetrics {
  total_lines: number
  avg_lines_per_file: number
  python_files: number
}
```

### Search Result

```typescript
interface SearchResult {
  artifact_id: string
  content: string
  metadata: ArtifactMetadata
  score: number
}

interface ArtifactMetadata {
  workspace_id: string
  filename: string
  file_type: string
  file_size: number
  created_at: string
  modified_at: string
  author?: string
  language?: string
  dependencies?: string[]
}
```

### Search Query

```typescript
interface SearchQuery {
  query: string
  top_k?: number
  workspace_ids?: string[]
  use_hybrid?: boolean
  filters?: SearchFilters
}

interface SearchFilters {
  file_types?: string[]
  date_range?: DateRange
  authors?: string[]
  languages?: string[]
}

interface DateRange {
  start: string
  end: string
}
```

## API Response Models

### Paginated Response

```typescript
interface PaginatedResponse<T> {
  data: T[]
  pagination: PaginationInfo
  metadata?: ResponseMetadata
}

interface PaginationInfo {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

interface ResponseMetadata {
  query_time_ms: number
  cache_hit: boolean
  source: 'cache' | 'api'
}
```

### API Response Wrapper

```typescript
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: ApiError
  timestamp: string
}

interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  stack?: string
}
```

## System Models

### Health Status

```typescript
interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  version: string
  services: ServiceHealth[]
}

interface ServiceHealth {
  name: string
  status: 'up' | 'down' | 'degraded'
  response_time_ms?: number
  last_check: string
  message?: string
}
```

### System Metrics

```typescript
interface SystemMetrics {
  uptime_seconds: number
  total_queries: number
  avg_query_time_ms: number
  error_rate: number
  memory_usage_mb: number
  cache_stats: CacheStats
  api_stats: ApiStats
}

interface CacheStats {
  hit_rate: number
  total_requests: number
  cache_size_mb: number
  evictions: number
}

interface ApiStats {
  total_requests: number
  success_rate: number
  avg_response_time_ms: number
  error_breakdown: Record<string, number>
}
```

## UI State Models

### Dashboard State

```typescript
interface DashboardState {
  workspaces: Workspace[]
  selected_workspace?: string
  search_query: string
  search_results: SearchResult[]
  is_loading: boolean
  error?: string
  filters: SearchFilters
  view_mode: 'grid' | 'list'
}
```

### User Preferences

```typescript
interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  language: string
  timezone: string
  notifications: NotificationSettings
  dashboard_layout: DashboardLayout
  search_defaults: SearchDefaults
}

interface NotificationSettings {
  email: boolean
  browser: boolean
  search_complete: boolean
  system_alerts: boolean
}

interface DashboardLayout {
  sidebar_collapsed: boolean
  default_view: 'overview' | 'search' | 'workspaces'
  items_per_page: number
}

interface SearchDefaults {
  default_top_k: number
  use_hybrid: boolean
  auto_search: boolean
}
```

## Form Models

### Search Form

```typescript
interface SearchFormData {
  query: string
  top_k: number
  workspace_ids: string[]
  use_hybrid: boolean
  filters: SearchFilters
}

interface SearchFormErrors {
  query?: string
  top_k?: string
  workspace_ids?: string
  filters?: Partial<SearchFilters>
}
```

### Workspace Filter Form

```typescript
interface WorkspaceFilterForm {
  status: ('active' | 'inactive' | 'error')[]
  date_range: DateRange
  min_artifacts: number
  max_artifacts: number
  tags: string[]
}
```

## API Contract Specifications

### REST API Endpoints

#### GET /api/workspaces
- **Response**: `PaginatedResponse<Workspace>`
- **Query Params**: `page`, `page_size`, `search`, `status`

#### GET /api/workspaces/{id}/profile
- **Response**: `ApiResponse<WorkspaceProfile>`
- **Path Params**: `id` (workspace ID)

#### POST /api/search
- **Request**: `SearchQuery`
- **Response**: `ApiResponse<PaginatedResponse<SearchResult>>`

#### GET /api/health
- **Response**: `ApiResponse<HealthStatus>`

#### GET /api/metrics
- **Response**: `ApiResponse<SystemMetrics>`

#### POST /api/admin/sync
- **Request**: `{ force_full?: boolean }`
- **Response**: `ApiResponse<SyncResponse>`

### WebSocket Events

#### search:progress
```typescript
interface SearchProgressEvent {
  type: 'search:progress'
  query_id: string
  progress: number
  message: string
}
```

#### workspace:updated
```typescript
interface WorkspaceUpdateEvent {
  type: 'workspace:updated'
  workspace_id: string
  changes: Partial<Workspace>
}
```

#### system:alert
```typescript
interface SystemAlertEvent {
  type: 'system:alert'
  level: 'info' | 'warning' | 'error'
  message: string
  timestamp: string
}
```

## Validation Schemas

### Zod Schemas (Recommended)

```typescript
import { z } from 'zod'

// Workspace validation
export const WorkspaceSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  artifact_count: z.number().int().min(0),
  last_updated: z.string().datetime(),
  created_at: z.string().datetime(),
  status: z.enum(['active', 'inactive', 'error'])
})

// Search query validation
export const SearchQuerySchema = z.object({
  query: z.string().min(1).max(500),
  top_k: z.number().int().min(1).max(100).default(10),
  workspace_ids: z.array(z.string().uuid()).optional(),
  use_hybrid: z.boolean().default(false),
  filters: SearchFiltersSchema.optional()
})

export const SearchFiltersSchema = z.object({
  file_types: z.array(z.string()).optional(),
  date_range: DateRangeSchema.optional(),
  authors: z.array(z.string()).optional(),
  languages: z.array(z.string()).optional()
})

export const DateRangeSchema = z.object({
  start: z.string().datetime(),
  end: z.string().datetime()
})
```

## Error Handling

### Error Types

```typescript
enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  SERVER_ERROR = 'SERVER_ERROR',
  RATE_LIMITED = 'RATE_LIMITED'
}

interface AppError {
  type: ErrorType
  message: string
  details?: Record<string, any>
  retryable: boolean
  timestamp: string
}
```

### Error Boundaries

```typescript
interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
  errorId: string
}
```

## Type Guards

```typescript
// Runtime type checking
export function isWorkspace(obj: any): obj is Workspace {
  return (
    typeof obj === 'object' &&
    typeof obj.id === 'string' &&
    typeof obj.name === 'string' &&
    typeof obj.artifact_count === 'number'
  )
}

export function isSearchResult(obj: any): obj is SearchResult {
  return (
    typeof obj === 'object' &&
    typeof obj.artifact_id === 'string' &&
    typeof obj.content === 'string' &&
    typeof obj.score === 'number'
  )
}
```

## Constants and Enums

```typescript
export enum WorkspaceStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error'
}

export enum FileType {
  PYTHON = 'python',
  NOTEBOOK = 'notebook',
  MARKDOWN = 'markdown',
  YAML = 'yaml',
  JSON = 'json',
  TEXT = 'text'
}

export enum SearchSortBy {
  RELEVANCE = 'relevance',
  DATE = 'date',
  SIZE = 'size',
  NAME = 'name'
}

export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100
export const SEARCH_DEBOUNCE_MS = 300
export const API_TIMEOUT_MS = 30000
```