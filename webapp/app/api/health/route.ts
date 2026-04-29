import { NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${PYTHON_API}/health`, { cache: 'no-store' })
    if (!res.ok) {
      return NextResponse.json(
        { status: 'unhealthy', timestamp: new Date().toISOString(), version: '1.0.0', services: [] },
        { status: res.status }
      )
    }
    const raw = await res.json()
    const now = new Date().toISOString()

    // Transform Python health shape → webapp HealthStatus shape
    const services = [
      {
        name: 'vector_store',
        status: raw.vector_store?.connected ? 'up' : 'down',
        last_check: now,
        message: raw.vector_store?.connected
          ? `${raw.vector_store.total_vectors ?? 0} vectors`
          : 'disconnected',
      },
      {
        name: 'embedding_service',
        status: raw.embedding_service?.model_loaded ? 'up' : 'down',
        last_check: now,
        message: raw.embedding_service?.model_name ?? 'not loaded',
      },
    ]

    return NextResponse.json({
      status: raw.status,
      timestamp: now,
      version: '1.0.0',
      services,
    })
  } catch (err) {
    console.error('[/api/health] fetch error:', err)
    return NextResponse.json(
      { status: 'unhealthy', timestamp: new Date().toISOString(), version: '1.0.0', services: [] },
      { status: 503 }
    )
  }
}
