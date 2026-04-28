# API Contracts: Search Functionality

## POST /api/search

Perform a semantic search across workspace artifacts.

### Request
```typescript
POST /api/search
Content-Type: application/json

interface SearchRequest {
  query: string                           // Search query text (1-500 chars)
  top_k?: number                         // Number of results (1-100, default: 10)
  workspace_ids?: string[]               // Limit search to specific workspaces
  use_hybrid?: boolean                   // Use hybrid search (default: false)
  filters?: SearchFilters                // Additional filters
}

interface SearchFilters {
  file_types?: string[]                  // Filter by file types
  date_range?: DateRange                 // Filter by date range
  authors?: string[]                     // Filter by authors
  languages?: string[]                   // Filter by programming languages
  min_score?: number                     // Minimum relevance score (0-1)
}

interface DateRange {
  start: string                          // ISO date string
  end: string                            // ISO date string
}
```

### Response
```typescript
interface SearchResponse {
  results: SearchResult[]
  total_found: number
  query_time_ms: number
  pagination?: PaginationInfo
  metadata: {
    query: string
    filters_applied: SearchFilters
    search_type: 'vector' | 'hybrid'
    cache_hit: boolean
  }
}

interface SearchResult {
  artifact_id: string
  content: string                        // Matched content snippet
  metadata: ArtifactMetadata
  score: number                          // Relevance score (0-1)
  highlights?: string[]                  // Highlighted matching terms
}

interface ArtifactMetadata {
  workspace_id: string
  workspace_name: string
  filename: string
  file_path: string
  file_type: string
  file_size: number
  created_at: string
  modified_at: string
  author?: string
  language?: string
  dependencies?: string[]
  line_number?: number                   // Line where match was found
}

interface PaginationInfo {
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}
```

### Error Responses
- `400 Bad Request`: Invalid query parameters or malformed request
- `422 Unprocessable Entity`: Query validation failed
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Search service unavailable
- `503 Service Unavailable`: Backend services down

### Examples

#### Basic Semantic Search
```bash
POST /api/search
Content-Type: application/json

{
  "query": "machine learning classification",
  "top_k": 20
}
```

#### Filtered Search
```bash
POST /api/search
Content-Type: application/json

{
  "query": "neural network",
  "top_k": 10,
  "workspace_ids": ["ws-123", "ws-456"],
  "use_hybrid": true,
  "filters": {
    "file_types": ["python", "notebook"],
    "languages": ["python"],
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-12-31T23:59:59Z"
    },
    "min_score": 0.7
  }
}
```

#### Response Example
```json
{
  "results": [
    {
      "artifact_id": "art-789",
      "content": "from sklearn.ensemble import RandomForestClassifier\nmodel = RandomForestClassifier()\nmodel.fit(X_train, y_train)",
      "metadata": {
        "workspace_id": "ws-123",
        "workspace_name": "ML Experiments",
        "filename": "classification.py",
        "file_path": "src/models/classification.py",
        "file_type": "python",
        "file_size": 2048,
        "created_at": "2024-03-15T10:30:00Z",
        "modified_at": "2024-03-20T14:45:00Z",
        "author": "john.doe",
        "language": "python",
        "dependencies": ["sklearn", "pandas", "numpy"],
        "line_number": 15
      },
      "score": 0.89,
      "highlights": ["RandomForestClassifier", "fit"]
    }
  ],
  "total_found": 1,
  "query_time_ms": 245,
  "metadata": {
    "query": "machine learning classification",
    "filters_applied": {},
    "search_type": "vector",
    "cache_hit": false
  }
}
```

## GET /api/search/suggestions

Get search query suggestions and autocomplete options.

### Request
```typescript
GET /api/search/suggestions
Query Parameters:
- q: string (partial query, 1-100 chars)
- limit?: number (max suggestions, default: 10)
- workspace_id?: string (limit to specific workspace)
```

### Response
```typescript
interface SearchSuggestionsResponse {
  suggestions: SearchSuggestion[]
  query: string
  total_suggestions: number
}

interface SearchSuggestion {
  text: string                          // Suggested query text
  type: 'completion' | 'related' | 'popular'
  score?: number                        // Relevance score
  count?: number                        // Number of results for this suggestion
}
```

### Examples
```bash
# Get autocomplete suggestions
GET /api/search/suggestions?q=machine%20learn

# Get suggestions for specific workspace
GET /api/search/suggestions?q=neural&workspace_id=ws-123
```

## GET /api/search/history

Get user's search history (future feature).

### Request
```typescript
GET /api/search/history
Query Parameters:
- limit?: number (default: 20)
- offset?: number (default: 0)
```

### Response
```typescript
interface SearchHistoryResponse {
  history: SearchHistoryItem[]
  total_count: number
  pagination: PaginationInfo
}

interface SearchHistoryItem {
  id: string
  query: string
  timestamp: string
  result_count: number
  filters?: SearchFilters
  is_saved: boolean
}
```

## POST /api/search/save

Save a search query for later use (future feature).

### Request
```typescript
POST /api/search/save
Content-Type: application/json

{
  "query": "machine learning classification",
  "name": "ML Classification Search",
  "description": "Search for ML classification implementations",
  "filters": { /* SearchFilters */ },
  "is_public": false
}
```

### Response
```typescript
interface SaveSearchResponse {
  id: string
  name: string
  query: string
  created_at: string
}
```

## Rate Limiting

- **Authenticated users**: 100 searches per minute
- **Anonymous users**: 10 searches per minute
- **Suggestions**: 60 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```