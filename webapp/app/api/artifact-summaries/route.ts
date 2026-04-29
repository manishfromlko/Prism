import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET(req: NextRequest) {
  const workspaceId = req.nextUrl.searchParams.get('workspace_id')
  const artifactId = req.nextUrl.searchParams.get('artifact_id')

  if (!workspaceId || !artifactId) {
    return NextResponse.json(
      { error: 'workspace_id and artifact_id are required' },
      { status: 400 }
    )
  }

  try {
    const query = new URLSearchParams({
      workspace_id: workspaceId,
      artifact_id: artifactId,
    })
    const res = await fetch(`${PYTHON_API}/artifact-summaries?${query}`, { cache: 'no-store' })
    if (res.status === 404) {
      return NextResponse.json({ error: 'Artifact summary not found' }, { status: 404 })
    }
    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch artifact summary' }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'Artifact summary service unavailable' }, { status: 503 })
  }
}
