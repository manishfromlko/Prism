'use client'

import Link from 'next/link'
import { useWorkspaces } from '@/hooks/use-api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { FolderOpen } from 'lucide-react'

export default function WorkspacesPage() {
  const { data: workspaces, isLoading, error } = useWorkspaces()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Workspaces</h1>
        <p className="text-muted-foreground">
          Browse all workspace profiles and open workspace analytics.
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, index) => (
            <Card key={index} className="p-6">
              <div className="space-y-4">
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-10 w-full" />
              </div>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardHeader>
            <CardTitle>Error loading workspaces</CardTitle>
            <CardDescription>
              Please refresh the page or try again later.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workspaces?.data?.map((workspace: any) => (
            <Card key={workspace.id} className="border">
              <CardHeader>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <CardTitle>{workspace.name}</CardTitle>
                    <CardDescription>{workspace.description || 'Workspace overview'}</CardDescription>
                  </div>
                  <Badge variant={workspace.status === 'active' ? 'default' : 'secondary'}>
                    {workspace.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-muted-foreground">
                    {workspace.artifact_count} artifacts
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Last updated {new Date(workspace.last_updated).toLocaleDateString()}
                  </div>
                  <Button asChild variant="outline" className="w-full">
                    <Link href={`/workspaces/${workspace.id}`}>View Workspace</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
