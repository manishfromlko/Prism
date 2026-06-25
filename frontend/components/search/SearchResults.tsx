'use client'

import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { FileText, FolderOpen, ExternalLink } from 'lucide-react'
import type { SearchResult, ArtifactMetadata } from '@/types'

interface SearchResultsProps {
  results?: SearchResult[]
  isLoading?: boolean
  error?: Error | null
  totalCount?: number
}

function getFileIcon(metadata: ArtifactMetadata) {
  if (metadata.file_type?.includes('folder')) {
    return <FolderOpen className="h-5 w-5 text-amber-500" />
  }
  return <FileText className="h-5 w-5 text-blue-500" />
}

function highlightText(text: string, highlights?: string[]) {
  if (!highlights || highlights.length === 0) {
    return text
  }

  // Sort by length descending to handle longer matches first
  const sortedHighlights = [...highlights].sort((a, b) => b.length - a.length)
  let result = text
  const spans: Array<{ start: number; end: number; highlight: string }> = []

  sortedHighlights.forEach((highlight) => {
    let startIndex = 0
    while ((startIndex = result.indexOf(highlight, startIndex)) !== -1) {
      spans.push({
        start: startIndex,
        end: startIndex + highlight.length,
        highlight,
      })
      startIndex += highlight.length
    }
  })

  // Sort spans and remove overlaps
  spans.sort((a, b) => a.start - b.start)
  const mergedSpans = spans.reduce((acc: typeof spans, span) => {
    const last = acc[acc.length - 1]
    if (last && span.start < last.end) {
      // Overlapping, extend the last span
      last.end = Math.max(last.end, span.end)
    } else {
      acc.push(span)
    }
    return acc
  }, [])

  // Build highlighted text
  let html = ''
  let lastEnd = 0

  mergedSpans.forEach((span) => {
    html += text.slice(lastEnd, span.start)
    html += `<mark>${text.slice(span.start, span.end)}</mark>`
    lastEnd = span.end
  })
  html += text.slice(lastEnd)

  return html
}

export function SearchResults({
  results = [],
  isLoading = false,
  error,
  totalCount = 0,
}: SearchResultsProps) {
  if (error) {
    return (
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Search Error</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {error.message || 'An error occurred while searching'}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!results || results.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Results</CardTitle>
          <CardDescription>
            Try adjusting your search query or filters to find what you're looking for
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Found {totalCount} result{totalCount !== 1 ? 's' : ''}
      </p>

      {results.map((result) => (
        <Card key={result.artifact_id} className="hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 flex-1">
                {getFileIcon(result.metadata)}
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-base line-clamp-2">
                    {result.metadata.filename}
                  </CardTitle>
                  {/* Use <div> not <p> (CardDescription) — Badge renders as <div> and
                      a <div> inside a <p> is invalid HTML causing hydration errors. */}
                  <div className="text-sm text-muted-foreground mt-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={`/workspaces/${result.metadata.workspace_id}`}
                        className="text-primary hover:underline text-xs"
                      >
                        {result.metadata.workspace_name}
                      </Link>
                      <span>•</span>
                      <span>{result.metadata.file_type}</span>
                      <span>•</span>
                      <span>
                        {(result.metadata.file_size / 1024).toFixed(1)} KB
                      </span>
                      {result.metadata.language && (
                        <>
                          <span>•</span>
                          <Badge variant="outline" className="text-xs">
                            {result.metadata.language}
                          </Badge>
                        </>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Modified {new Date(result.metadata.modified_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link
                  href={`/workspaces/${result.metadata.workspace_id}?file=${result.artifact_id}`}
                >
                  <ExternalLink className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="bg-muted p-3 rounded-md">
              <p className="text-sm text-foreground line-clamp-3">
                {result.content}
              </p>
              <div className="flex items-center justify-between mt-3">
                <p className="text-xs text-muted-foreground">
                  Relevance Score: {(result.score * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}