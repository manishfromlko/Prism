import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()

    // Forward to Python /query endpoint (same shape, just renamed)
    const res = await fetch(`${PYTHON_API}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: body.query,
        top_k: body.top_k ?? 10,
        workspace_ids: body.workspace_ids ?? null,
        use_hybrid: body.use_hybrid ?? false,
      }),
      cache: 'no-store',
    })

    if (!res.ok) {
      const text = await res.text()
      return NextResponse.json({ error: text }, { status: res.status })
    }

    const raw = await res.json()

    // Transform Python response → webapp SearchResult shape
    const data = (raw.results ?? []).map((r: any) => {
      const meta = r.metadata ?? {}
      const filePath: string = meta.path ?? ''
      const filename = filePath.split('/').pop() || r.artifact_id || ''
      const fileType: string = meta.type ?? meta.file_type ?? ''

      return {
        artifact_id: r.artifact_id,
        content: r.content ?? '',
        score: r.score ?? 0,
        metadata: {
          workspace_id: meta.workspace_id ?? '',
          workspace_name: meta.workspace_name ?? meta.workspace_id ?? '',
          filename,
          file_path: filePath,
          file_type: fileType,
          file_size: meta.size ?? meta.size_bytes ?? 0,
          modified_at: meta.modified_at ?? '',
          created_at: meta.modified_at ?? '',
          language: fileType === 'notebook' ? 'Python' : fileType === 'python' ? 'Python' : undefined,
        },
      }
    })

    return NextResponse.json({
      data,
      metadata: {
        query_time_ms: raw.query_time_ms,
        total_found: raw.total_found,
        cache_hit: false,
        source: 'api',
      },
    })
  } catch (err) {
    console.error('[/api/search] fetch error:', err)
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 })
  }
}
