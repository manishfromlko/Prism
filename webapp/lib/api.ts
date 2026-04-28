import { QueryClient } from '@tanstack/react-query'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_TIMEOUT = 30000

// Create Query Client with default options
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.status >= 400 && error?.status < 500) {
          return false
        }
        // Retry up to 3 times for other errors
        return failureCount < 3
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
})

// API Client class
class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        )
      }

      return await response.json()
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Workspace endpoints
  async getWorkspaces(params?: {
    page?: number
    page_size?: number
    search?: string
    status?: string
  }) {
    const searchParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.set(key, String(value))
        }
      })
    }

    const query = searchParams.toString()
    const endpoint = `/api/workspaces${query ? `?${query}` : ''}`

    return this.request(endpoint)
  }

  async getWorkspace(id: string) {
    return this.request(`/api/workspaces/${id}`)
  }

  async getWorkspaceProfile(id: string) {
    return this.request(`/api/workspaces/${id}/profile`)
  }

  // Search endpoints
  async search(query: any) {
    return this.request('/api/search', {
      method: 'POST',
      body: JSON.stringify(query),
    })
  }

  async getSearchSuggestions(q: string, workspace_id?: string) {
    const params = new URLSearchParams({ q })
    if (workspace_id) {
      params.set('workspace_id', workspace_id)
    }

    return this.request(`/api/search/suggestions?${params}`)
  }

  // System endpoints
  async getHealth() {
    return this.request('/api/health')
  }

  async getMetrics() {
    return this.request('/api/metrics')
  }

  async syncData(options?: { force_full?: boolean }) {
    return this.request('/api/admin/sync', {
      method: 'POST',
      body: JSON.stringify(options || {}),
    })
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL)

// Query keys for React Query
export const queryKeys = {
  workspaces: ['workspaces'] as const,
  workspace: (id: string) => ['workspaces', id] as const,
  workspaceProfile: (id: string) => ['workspaces', id, 'profile'] as const,
  search: (query: any) => ['search', query] as const,
  searchSuggestions: (q: string, workspaceId?: string) => [
    'search',
    'suggestions',
    q,
    workspaceId,
  ] as const,
  health: ['health'] as const,
  metrics: ['metrics'] as const,
}