'use client'

import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { FileText, FolderOpen, ExternalLink, Calendar } from 'lucide-react'
import type { ArtifactMetadata } from '@/types'

interface ArtifactListProps {
  artifacts?: ArtifactMetadata[]
  isLoading?: boolean
  workspaceId: string
}

function getFileIcon(fileType?: string) {
  if (fileType?.includes('folder')) {
    return <FolderOpen className="h-4 w-4 text-amber-500" />
  }
  return <FileText className="h-4 w-4 text-blue-500" />
}

function getLanguageColor(language?: string) {
  const colors: Record<string, string> = {
    python: 'bg-blue-100 text-blue-800',
    javascript: 'bg-yellow-100 text-yellow-800',
    typescript: 'bg-blue-100 text-blue-800',
    sql: 'bg-green-100 text-green-800',
    markdown: 'bg-gray-100 text-gray-800',
    yaml: 'bg-purple-100 text-purple-800',
    json: 'bg-orange-100 text-orange-800',
    java: 'bg-red-100 text-red-800',
    'c++': 'bg-pink-100 text-pink-800',
  }
  return colors[language?.toLowerCase() || ''] || 'bg-gray-100 text-gray-800'
}

export function ArtifactList({ artifacts = [], isLoading = false, workspaceId }: ArtifactListProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Artifacts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center space-x-3">
                <Skeleton className="h-8 w-8 rounded" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!artifacts || artifacts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Artifacts</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">No artifacts found</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Artifacts</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {artifacts.slice(0, 10).map((artifact) => (
            (() => {
              const artifactId = artifact.artifact_id || `${workspaceId}:${artifact.file_path}`
              const href = `/workspaces/${workspaceId}?file=${encodeURIComponent(artifact.file_path)}&artifact_id=${encodeURIComponent(artifactId)}`
              return (
            <div
              key={`${artifact.workspace_id}-${artifact.file_path}`}
              className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {getFileIcon(artifact.file_type)}
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-sm truncate">{artifact.filename}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-muted-foreground">
                      {(artifact.file_size / 1024).toFixed(1)} KB
                    </span>
                    {artifact.language && (
                      <Badge
                        variant="outline"
                        className={`text-xs ${getLanguageColor(artifact.language)}`}
                      >
                        {artifact.language}
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(artifact.modified_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="ml-2 h-8 w-8 p-0"
              >
                <a href={href}>
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            </div>
              )
            })()
          ))}
        </div>
      </CardContent>
    </Card>
  )
}