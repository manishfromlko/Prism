import { NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  try {
    const res = await fetch(`${PYTHON_API}/user-profiles/${encodeURIComponent(id)}`, { cache: 'no-store' })
    if (res.status === 404) {
      return NextResponse.json({ error: `Profile for '${id}' not found` }, { status: 404 })
    }
    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch profile' }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'User profile service unavailable' }, { status: 503 })
  }
}
