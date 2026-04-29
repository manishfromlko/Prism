import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params
  try {
    const res = await fetch(
      `${PYTHON_API}/profile/workspace/${encodeURIComponent(id)}`,
      { cache: 'no-store' }
    )
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json({ error: text }, { status: res.status })
    }
    const profile = await res.json()
    // Wrap in { data } to match the shape useWorkspaceProfile expects
    return NextResponse.json({ data: profile })
  } catch (err) {
    console.error(`[/api/workspaces/${id}/profile] fetch error:`, err)
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 })
  }
}
