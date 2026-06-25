'use client'

import { useMetrics } from '@/hooks/use-api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

export default function AnalyticsPage() {
  const { data, isLoading, error } = useMetrics()

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Analytics</CardTitle>
          <CardDescription>Unable to load analytics data.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">System metrics and usage signals for the workspace dashboard.</p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, index) => (
            <Card key={index} className="p-6">
              <Skeleton className="h-6 w-1/3 mb-4" />
              <Skeleton className="h-10 w-full" />
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Uptime</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{data?.uptime_seconds ?? '—'}s</p>
              <p className="text-sm text-muted-foreground">Total service uptime.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Queries</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{data?.total_queries ?? '—'}</p>
              <p className="text-sm text-muted-foreground">Total requests processed.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Error Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant={data?.error_rate > 0.05 ? 'destructive' : 'default'}>
                {(data?.error_rate ?? 0).toFixed(2)}%
              </Badge>
              <p className="text-sm text-muted-foreground mt-2">Average request error rate.</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
