import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, queryKeys } from '@/lib/api'
import type {
  Workspace,
  WorkspaceProfile,
  SearchResult,
  SearchQuery,
  HealthStatus,
  SystemMetrics,
  ApiResponse,
  PaginatedResponse,
} from '@/types'

// Workspace hooks
export function useWorkspaces(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
}) {
  return useQuery({
    queryKey: [...queryKeys.workspaces, params],
    queryFn: () => apiClient.getWorkspaces(params),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useWorkspace(id: string) {
  return useQuery({
    queryKey: queryKeys.workspace(id),
    queryFn: () => apiClient.getWorkspace(id),
    enabled: !!id,
  })
}

export function useWorkspaceProfile(id: string) {
  return useQuery({
    queryKey: queryKeys.workspaceProfile(id),
    queryFn: () => apiClient.getWorkspaceProfile(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Search hooks
export function useSearch(query: SearchQuery, enabled = true) {
  return useQuery({
    queryKey: queryKeys.search(query),
    queryFn: () => apiClient.search(query),
    enabled: enabled && !!query.query,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

export function useSearchSuggestions(q: string, workspaceId?: string) {
  return useQuery({
    queryKey: queryKeys.searchSuggestions(q, workspaceId),
    queryFn: () => apiClient.getSearchSuggestions(q, workspaceId),
    enabled: q.length > 2,
    staleTime: 30 * 1000, // 30 seconds
  })
}

// System hooks
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30 * 1000, // 30 seconds
  })
}

export function useMetrics() {
  return useQuery({
    queryKey: queryKeys.metrics,
    queryFn: () => apiClient.getMetrics(),
    refetchInterval: 60 * 1000, // 1 minute
  })
}

// Mutation hooks
export function useSyncData() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (options?: { force_full?: boolean }) => apiClient.syncData(options),
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces })
      queryClient.invalidateQueries({ queryKey: queryKeys.metrics })
    },
  })
}

// Custom hooks for common patterns
export function useWorkspaceStats() {
  const { data: workspaces } = useWorkspaces()

  return {
    totalWorkspaces: workspaces?.data?.length || 0,
    activeWorkspaces: workspaces?.data?.filter(w => w.status === 'active').length || 0,
    totalArtifacts: workspaces?.data?.reduce((sum, w) => sum + w.artifact_count, 0) || 0,
    isLoading: !workspaces,
  }
}

export function useSearchWithDebounce(query: SearchQuery, debounceMs = 300) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [query, debounceMs])

  return useSearch(debouncedQuery, !!debouncedQuery.query)
}

// Error handling utilities
export function useApiErrorHandler() {
  const queryClient = useQueryClient()

  return (error: any) => {
    console.error('API Error:', error)

    // Handle specific error types
    if (error?.status === 401) {
      // Handle authentication error
      // Could redirect to login or refresh token
    } else if (error?.status === 403) {
      // Handle authorization error
    } else if (error?.status >= 500) {
      // Handle server errors
    }

    // Could show toast notification here
  }
}

// Loading states
export function useLoadingState(queries: any[]) {
  return {
    isLoading: queries.some(query => query.isLoading),
    isError: queries.some(query => query.isError),
    isSuccess: queries.every(query => query.isSuccess),
    error: queries.find(query => query.error)?.error,
  }
}