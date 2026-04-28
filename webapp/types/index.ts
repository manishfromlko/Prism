// Core data models for the webapp frontend
// Based on specs/003-webapp-frontend/data-model.md

// Workspace types
export interface Workspace {
  id: string
  name: string
  description?: string
  artifact_count: number
  last_updated: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
  tags?: string[]
}

export interface WorkspaceProfile {
  workspace_id: string
  artifact_count: number
  top_tools: ToolUsage[]
  top_topics: TopicRelevance[]
  collaboration_patterns: CollaborationMetrics
  last_updated?: string
  file_types: Record<string, number>
  code_metrics: CodeMetrics
}

export interface ToolUsage {
  tool: string
  count: number
}

export interface TopicRelevance {
  topic: string
  relevance: number
}

export interface CollaborationMetrics {
  total_artifacts: number
  notebooks_count: number
  scripts_count: number
  avg_file_size: number
}

export interface CodeMetrics {
  total_lines: number
  avg_lines_per_file: number
  python_files: number
}

// Search types
export interface SearchResult {
  artifact_id: string
  content: string
  metadata: ArtifactMetadata
  score: number
  highlights?: string[]
}

export interface ArtifactMetadata {
  workspace_id: string
  workspace_name: string
  filename: string
  file_path: string
  file_type: string
  file_size: number
  created_at: string
  modified_at: string
  author?: string
  language?: string
  dependencies?: string[]
  line_number?: number
}

export interface SearchQuery {
  query: string
  top_k?: number
  workspace_ids?: string[]
  use_hybrid?: boolean
  filters?: SearchFilters
}

export interface SearchFilters {
  file_types?: string[]
  date_range?: DateRange
  authors?: string[]
  languages?: string[]
  min_score?: number
}

export interface DateRange {
  start: string
  end: string
}

// API Response types
export interface PaginatedResponse<T> {
  data: T[]
  pagination: PaginationInfo
  metadata?: ResponseMetadata
}

export interface PaginationInfo {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface ResponseMetadata {
  query_time_ms: number
  cache_hit: boolean
  source: 'cache' | 'api'
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: ApiError
  timestamp: string
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  stack?: string
}

// System types
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  version: string
  services: ServiceHealth[]
}

export interface ServiceHealth {
  name: string
  status: 'up' | 'down' | 'degraded'
  response_time_ms?: number
  last_check: string
  message?: string
}

export interface SystemMetrics {
  uptime_seconds: number
  total_queries: number
  avg_query_time_ms: number
  error_rate: number
  memory_usage_mb: number
  cache_stats: CacheStats
  api_stats: ApiStats
}

export interface CacheStats {
  hit_rate: number
  total_requests: number
  cache_size_mb: number
  evictions: number
}

export interface ApiStats {
  total_requests: number
  success_rate: number
  avg_response_time_ms: number
  error_breakdown: Record<string, number>
}

// UI State types
export interface DashboardState {
  workspaces: Workspace[]
  selected_workspace?: string
  search_query: string
  search_results: SearchResult[]
  is_loading: boolean
  error?: string
  filters: SearchFilters
  view_mode: 'grid' | 'list'
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  language: string
  timezone: string
  notifications: NotificationSettings
  dashboard_layout: DashboardLayout
  search_defaults: SearchDefaults
}

export interface NotificationSettings {
  email: boolean
  browser: boolean
  search_complete: boolean
  system_alerts: boolean
}

export interface DashboardLayout {
  sidebar_collapsed: boolean
  default_view: 'overview' | 'search' | 'workspaces'
  items_per_page: number
}

export interface SearchDefaults {
  default_top_k: number
  use_hybrid: boolean
  auto_search: boolean
}

// Form types
export interface SearchFormData {
  query: string
  top_k: number
  workspace_ids: string[]
  use_hybrid: boolean
  filters: SearchFilters
}

export interface SearchFormErrors {
  query?: string
  top_k?: string
  workspace_ids?: string
  filters?: Partial<SearchFilters>
}

export interface WorkspaceFilterForm {
  status: ('active' | 'inactive' | 'error')[]
  date_range: DateRange
  min_artifacts: number
  max_artifacts: number
  tags: string[]
}

// Constants and enums
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

// Error types
export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  SERVER_ERROR = 'SERVER_ERROR',
  RATE_LIMITED = 'RATE_LIMITED'
}

export interface AppError {
  type: ErrorType
  message: string
  details?: Record<string, any>
  retryable: boolean
  timestamp: string
}

// Error boundary state
export interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
  errorId: string
}