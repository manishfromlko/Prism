import { QueryClient } from '@tanstack/react-query'

// API Configuration
// Empty string → relative URLs → requests go to Next.js /api/* routes on the same origin.
// The Next.js API routes then proxy to the Python backend (PYTHON_API_URL, default localhost:8000).
const API_BASE_URL = ''
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
  }): Promise<{ data: any[]; pagination: any; metadata?: any }> {
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

  async getWorkspace(id: string): Promise<any> {
    return this.request(`/api/workspaces/${id}`)
  }

  async getWorkspaceProfile(id: string): Promise<any> {
    return this.request(`/api/workspaces/${id}/profile`)
  }

  // Search endpoints
  async search(query: any): Promise<{ data: any[]; metadata?: any }> {
    return this.request('/api/search', {
      method: 'POST',
      body: JSON.stringify(query),
    })
  }

  async getSearchSuggestions(q: string, workspace_id?: string): Promise<string[]> {
    const params = new URLSearchParams({ q })
    if (workspace_id) {
      params.set('workspace_id', workspace_id)
    }

    return this.request(`/api/search/suggestions?${params}`)
  }

  // System endpoints
  async getHealth(): Promise<{ status: string; timestamp: string; version: string; services: any[] }> {
    return this.request('/api/health')
  }

  async getMetrics(): Promise<any> {
    return this.request('/api/metrics')
  }

  async syncData(options?: { force_full?: boolean }): Promise<any> {
    return this.request('/api/admin/sync', {
      method: 'POST',
      body: JSON.stringify(options || {}),
    })
  }

  // User profile endpoints
  async getUserProfiles(): Promise<{ data: UserProfile[]; total: number }> {
    return this.request('/api/user-profiles')
  }

  async getUserProfile(userId: string): Promise<{ data: UserProfile }> {
    return this.request(`/api/user-profiles/${encodeURIComponent(userId)}`)
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL)

export interface UserProfile {
  id: string
  user_id: string
  user_profile: string
  tags: string[]
}

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
  userProfiles: ['user-profiles'] as const,
  userProfile: (id: string) => ['user-profiles', id] as const,
}