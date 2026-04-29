import { NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${PYTHON_API}/metrics`, { cache: 'no-store' })
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json({ error: text }, { status: res.status })
    }
    // Python MetricsResponse fields match what AnalyticsPage expects directly
    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    console.error('[/api/metrics] fetch error:', err)
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 })
  }
}
