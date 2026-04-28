'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { ToolUsage } from '@/types'

interface ToolChartProps {
  data?: ToolUsage[]
  isLoading?: boolean
}

export function ToolChart({ data = [], isLoading = false }: ToolChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-muted animate-pulse rounded" />
        </CardContent>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">No tool usage data available</p>
        </CardContent>
      </Card>
    )
  }

  // Sort data by count descending and take top 10
  const chartData = [...data].sort((a, b) => b.count - a.count).slice(0, 10)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Tools Used</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tool" angle={-45} textAnchor="end" height={80} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" name="Usage Count" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}