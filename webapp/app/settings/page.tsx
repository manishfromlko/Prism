'use client'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Application settings are coming soon. You can return to the dashboard for now.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Settings coming soon</CardTitle>
          <CardDescription>
            Static settings and preferences will be added in the next iteration.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Manage your workspace dashboard preferences and account settings from here.
          </p>
          <Button asChild>
            <Link href="/">Back to dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
