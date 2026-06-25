import { NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${PYTHON_API}/user-profiles`, { cache: 'no-store' })
    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch user profiles' }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'User profile service unavailable' }, { status: 503 })
  }
}
