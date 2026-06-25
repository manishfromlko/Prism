'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowUpRight, FileText, Code2, Users } from 'lucide-react'
import type { WorkspaceProfile } from '@/types'

interface InsightPanelProps {
  profile?: WorkspaceProfile
  isLoading?: boolean
}

export function InsightPanel({ profile, isLoading = false }: InsightPanelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workspace Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="h-16 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!profile) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workspace Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">No insight data available for this workspace.</p>
        </CardContent>
      </Card>
    )
  }

  const fileTypeEntries = Object.entries(profile.file_types || {})
  const topTopics = profile.top_topics?.slice(0, 5) || []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workspace Insights</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-4">
            <div className="rounded-lg border border-border p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                <ArrowUpRight className="h-4 w-4" />
                Collaboration & code metrics
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Artifacts</p>
                    <p className="text-lg font-semibold">{profile.collaboration_patterns.total_artifacts}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Notebooks</p>
                    <p className="text-lg font-semibold">{profile.collaboration_patterns.notebooks_count}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Scripts</p>
                    <p className="text-lg font-semibold">{profile.collaboration_patterns.scripts_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Avg. File Size</p>
                    <p className="text-lg font-semibold">{profile.collaboration_patterns.avg_file_size.toFixed(1)} KB</p>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Lines</p>
                    <p className="text-lg font-semibold">{profile.code_metrics.total_lines}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Avg. Lines/File</p>
                    <p className="text-lg font-semibold">{profile.code_metrics.avg_lines_per_file.toFixed(1)}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-border p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                <Code2 className="h-4 w-4" />
                File type distribution
              </div>
              <div className="space-y-2">
                {fileTypeEntries.length > 0 ? (
                  fileTypeEntries.map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between text-sm">
                      <span>{type}</span>
                      <span className="font-semibold">{count}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground text-sm">No file type data available</p>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
              <Users className="h-4 w-4" />
              Top topics
            </div>
            <div className="space-y-2">
              {topTopics.length > 0 ? (
                topTopics.map((topic) => (
                  <Badge key={topic.topic} variant="outline" className="text-sm">
                    {topic.topic} ({Math.round(topic.relevance * 100)}%)
                  </Badge>
                ))
              ) : (
                <p className="text-muted-foreground text-sm">No topics available yet.</p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
