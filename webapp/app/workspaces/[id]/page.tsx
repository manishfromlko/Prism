'use client'

import dynamic from 'next/dynamic'
import { useParams, useSearchParams } from 'next/navigation'
import { useWorkspace, useWorkspaceProfile, useArtifactSummary, useWorkspaceArtifactSummaries } from '@/hooks/use-api'
import { ProfileCard } from '@/components/workspace/ProfileCard'
import { ArtifactList } from '@/components/workspace/ArtifactList'
import { InsightPanel } from '@/components/workspace/InsightPanel'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

const ToolChart = dynamic(
  () => import('@/components/workspace/ToolChart').then((mod) => mod.ToolChart),
  { ssr: false }
)

export default function WorkspaceDetailPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const workspaceId = typeof params?.id === 'string' ? params.id : ''
  const selectedFile = searchParams.get('file') || undefined
  const selectedArtifactId = searchParams.get('artifact_id') || (selectedFile ? `${workspaceId}:${selectedFile}` : '')

  const { data: workspaceData, isLoading: workspaceLoading, error: workspaceError } = useWorkspace(workspaceId)
  const {
    data: profileData,
    isLoading: profileLoading,
    error: profileError,
  } = useWorkspaceProfile(workspaceId)
  const {
    data: artifactSummaryData,
    isLoading: artifactSummaryLoading,
    error: artifactSummaryError,
  } = useArtifactSummary(workspaceId, selectedArtifactId)
  const {
    data: workspaceSummariesData,
    isLoading: workspaceSummariesLoading,
  } = useWorkspaceArtifactSummaries(workspaceId)

  const workspace = workspaceData?.data
  const profile = profileData?.data
  const summariesByArtifactId = Object.fromEntries(
    (workspaceSummariesData?.data || []).map((summary) => [summary.artifact_id, summary])
  )

  if (workspaceError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load workspace details. Please try again later.
        </AlertDescription>
      </Alert>
    )
  }

  if (workspaceLoading) {
    return (
      <div className="space-y-4">
        <Card className="animate-pulse">
          <CardHeader>
            <CardTitle>Loading workspace details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-40 bg-muted rounded" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!workspace) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workspace not found</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">The selected workspace could not be loaded.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">{workspace.name}</h1>
        <p className="text-muted-foreground">Workspace profile and artifact analytics.</p>
      </div>

      {profileError && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Workspace metrics are unavailable right now. The core workspace profile is still shown.
          </AlertDescription>
        </Alert>
      )}

      {selectedFile && (
        <Card>
          <CardHeader>
            <CardTitle>Selected Artifact</CardTitle>
            <CardDescription>File filter is active for the selected artifact.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{selectedFile}</p>
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium">Artifact Summary</p>
              {artifactSummaryLoading && (
                <p className="text-sm text-muted-foreground">Loading summary...</p>
              )}
              {!artifactSummaryLoading && artifactSummaryData?.data && (
                <>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {artifactSummaryData.data.artifact_summary}
                  </p>
                  {artifactSummaryData.data.tags?.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Tags: {artifactSummaryData.data.tags.join(', ')}
                    </p>
                  )}
                </>
              )}
              {!artifactSummaryLoading && artifactSummaryError && (
                <p className="text-sm text-muted-foreground">
                  Summary unavailable for this artifact.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <div className="space-y-6">
          <ProfileCard workspace={workspace} />
          <InsightPanel profile={profile} isLoading={profileLoading} />
        </div>

        <div className="space-y-6">
          <ToolChart data={profile?.top_tools || []} isLoading={profileLoading} />
          <ArtifactList
            workspaceId={workspaceId}
            artifacts={profile?.recent_artifacts || []}
            isLoading={profileLoading}
            summariesByArtifactId={summariesByArtifactId}
            summariesLoading={workspaceSummariesLoading}
          />
        </div>
      </div>
    </div>
  )
}
