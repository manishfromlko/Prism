import { NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function POST() {
  try {
    const res = await fetch(`${PYTHON_API}/admin/sync-profiles-from-summaries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    })
    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json({ error: text }, { status: res.status })
    }
    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    console.error('[/api/admin/sync-profiles-from-summaries] fetch error:', err)
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 })
  }
}
