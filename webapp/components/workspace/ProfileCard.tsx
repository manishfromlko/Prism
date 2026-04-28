'use client'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileText, FolderOpen, Calendar, User } from 'lucide-react'
import type { Workspace } from '@/types'

interface ProfileCardProps {
  workspace: Workspace
}

export function ProfileCard({ workspace }: ProfileCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <FolderOpen className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle className="text-2xl">{workspace.name}</CardTitle>
              {workspace.description && (
                <CardDescription className="mt-1">
                  {workspace.description}
                </CardDescription>
              )}
            </div>
          </div>
          <Badge variant={workspace.status === 'active' ? 'default' : 'secondary'}>
            {workspace.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Total Artifacts
            </p>
            <p className="text-2xl font-bold">{workspace.artifact_count}</p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Last Updated
            </p>
            <p className="text-sm font-medium">
              {new Date(workspace.last_updated).toLocaleDateString()}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Created
            </p>
            <p className="text-sm font-medium">
              {new Date(workspace.created_at).toLocaleDateString()}
            </p>
          </div>
          {workspace.tags && workspace.tags.length > 0 && (
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Tags</p>
              <div className="flex flex-wrap gap-1">
                {workspace.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}