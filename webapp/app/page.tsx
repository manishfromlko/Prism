'use client'

import { useWorkspaces, useWorkspaceStats, useHealth } from '@/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  FolderOpen,
  FileText,
  Activity,
  AlertCircle,
  TrendingUp,
  Users,
  Search as SearchIcon,
} from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const { data: workspaces, isLoading: workspacesLoading, error: workspacesError } = useWorkspaces()
  const { data: health, isLoading: healthLoading } = useHealth()
  const stats = useWorkspaceStats()

  if (workspacesError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load workspaces. Please try again later.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your workspaces and system status
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Workspaces</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {stats.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats.totalWorkspaces}</div>
            )}
            <p className="text-xs text-muted-foreground">
              {stats.activeWorkspaces} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Artifacts</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {stats.isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats.totalArtifacts}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Across all workspaces
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {healthLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">
                <Badge variant={health?.status === 'healthy' ? 'default' : 'destructive'}>
                  {health?.status || 'Unknown'}
                </Badge>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              API services status
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1</div>
            <p className="text-xs text-muted-foreground">
              Current session
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Workspaces */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Workspaces</CardTitle>
          <CardDescription>
            Your most recently accessed workspaces
          </CardDescription>
        </CardHeader>
        <CardContent>
          {workspacesLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : workspaces?.data?.length ? (
            <div className="space-y-4">
              {workspaces.data.slice(0, 5).map((workspace) => (
                <div
                  key={workspace.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    <div className="h-10 w-10 rounded bg-primary/10 flex items-center justify-center">
                      <FolderOpen className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-medium">{workspace.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {workspace.artifact_count} artifacts • Last updated {new Date(workspace.last_updated).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant={workspace.status === 'active' ? 'default' : 'secondary'}>
                      {workspace.status}
                    </Badge>
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/workspaces/${workspace.id}`}>
                        View
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FolderOpen className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No workspaces found</h3>
              <p className="text-muted-foreground">
                Get started by creating your first workspace.
              </p>
              <Button asChild className="mt-4">
                <Link href="/workspaces/new">Create Workspace</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common tasks and shortcuts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/search">
                <SearchIcon className="h-6 w-6 mb-2" />
                Search Artifacts
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/workspaces">
                <FolderOpen className="h-6 w-6 mb-2" />
                Browse Workspaces
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-20 flex-col">
              <Link href="/analytics">
                <TrendingUp className="h-6 w-6 mb-2" />
                View Analytics
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}