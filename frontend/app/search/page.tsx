'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSearch } from '@/hooks/use-api'
import { SearchBar } from '@/components/search/SearchBar'
import { SearchResults } from '@/components/search/SearchResults'
import { SearchFilters } from '@/components/search/SearchFilters'
import { Card } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'
import type { SearchQuery, SearchFilters as SearchFiltersType } from '@/types'

function SearchPageContent() {
  const searchParams = useSearchParams()
  const initialQuery = searchParams.get('q') || ''

  const [query, setQuery] = useState(initialQuery)
  const [filters, setFilters] = useState<Partial<SearchFiltersType>>({})
  const [searchQuery, setSearchQuery] = useState<SearchQuery | null>(null)

  // Perform search when query or filters change
  useEffect(() => {
    if (query.trim()) {
      setSearchQuery({
        query,
        top_k: 20,
        use_hybrid: true,
        filters: filters as any,
      })
    }
  }, [query, filters])

  const { data: searchResults, isLoading, error } = useSearch(
    searchQuery || { query: '', top_k: 20, use_hybrid: true },
    !!searchQuery
  )

  const handleSearch = (newQuery: string) => {
    setQuery(newQuery)
  }

  const handleFilterChange = (newFilters: Partial<SearchFiltersType>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
    }))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Find artifacts across your workspaces using semantic search
        </p>
      </div>

      {/* Search Bar */}
      <div className="sticky top-0 z-10 -mx-6 -mt-6 bg-background px-6 py-6 border-b">
        <SearchBar
          onSearch={handleSearch}
          defaultValue={query}
          placeholder="Search code, notebooks, documentation..."
        />
      </div>

      {/* Search Guidance */}
      {!query && (
        <Card className="border-dashed bg-card/50">
          <div className="p-8 text-center">
            <h3 className="text-lg font-medium mb-2">Start Searching</h3>
            <p className="text-muted-foreground mb-4">
              Enter a query to search across all workspaces. Try searching for:
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {[
                'machine learning',
                'data processing',
                'API endpoints',
                'database queries',
                'error handling',
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => handleSearch(example)}
                  className="px-3 py-1 rounded-full bg-primary/10 text-primary hover:bg-primary/20 text-sm"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* Results Section */}
      {query && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-32">
              <SearchFilters
                onFilterChange={handleFilterChange}
                defaultFilters={filters}
              />
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-3">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error
                    ? error.message
                    : 'An error occurred while searching'}
                </AlertDescription>
              </Alert>
            )}

            {isLoading && (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <Card key={i} className="h-32 animate-pulse" />
                ))}
              </div>
            )}

            {!isLoading && (
              <SearchResults
                results={searchResults?.data || []}
                totalCount={searchResults?.data?.length || 0}
                error={error}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchPageContent />
    </Suspense>
  )
}