'use client'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export default function NewWorkspacePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create Workspace</h1>
        <p className="text-muted-foreground">
          This functionality is coming soon. For now, you can browse existing workspaces.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workspace creation coming soon</CardTitle>
          <CardDescription>
            The workspace management flow is under development.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Create workspace onboarding will be available in a future release.
          </p>
          <Button asChild>
            <Link href="/workspaces">Back to workspaces</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
