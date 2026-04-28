# API Contracts: Workspace Management

## GET /api/workspaces

Retrieve a paginated list of workspaces.

### Request
```typescript
GET /api/workspaces
Query Parameters:
- page?: number (default: 1)
- page_size?: number (default: 20, max: 100)
- search?: string (workspace name filter)
- status?: 'active' | 'inactive' | 'error'
- sort_by?: 'name' | 'updated' | 'created' | 'artifacts'
- sort_order?: 'asc' | 'desc' (default: 'desc')
```

### Response
```typescript
interface PaginatedWorkspacesResponse {
  data: Workspace[]
  pagination: {
    page: number
    page_size: number
    total_count: number
    total_pages: number
    has_next: boolean
    has_previous: boolean
  }
  metadata: {
    query_time_ms: number
    filtered_count: number
  }
}

interface Workspace {
  id: string
  name: string
  description?: string
  artifact_count: number
  last_updated: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
  tags?: string[]
}
```

### Error Responses
- `400 Bad Request`: Invalid query parameters
- `500 Internal Server Error`: Server error

### Examples
```bash
# Get first page of workspaces
GET /api/workspaces

# Search for workspaces with pagination
GET /api/workspaces?page=2&page_size=10&search=machine%20learning

# Get only active workspaces sorted by artifact count
GET /api/workspaces?status=active&sort_by=artifacts&sort_order=desc
```

## GET /api/workspaces/{id}

Retrieve detailed information about a specific workspace.

### Request
```typescript
GET /api/workspaces/{id}
Path Parameters:
- id: string (workspace UUID)
```

### Response
```typescript
interface WorkspaceDetailResponse {
  id: string
  name: string
  description?: string
  artifact_count: number
  last_updated: string
  created_at: string
  status: 'active' | 'inactive' | 'error'
  tags?: string[]
  statistics: {
    total_size_bytes: number
    file_type_breakdown: Record<string, number>
    language_breakdown: Record<string, number>
    author_breakdown: Record<string, number>
  }
  recent_activity: {
    last_commit?: string
    last_modified_files: string[]
    contributor_count: number
  }
}
```

### Error Responses
- `404 Not Found`: Workspace not found
- `500 Internal Server Error`: Server error

## POST /api/workspaces

Create a new workspace (future feature).

### Request
```typescript
POST /api/workspaces
Content-Type: application/json

{
  "name": "My New Workspace",
  "description": "Description of the workspace",
  "tags": ["tag1", "tag2"]
}
```

### Response
```typescript
interface CreateWorkspaceResponse {
  id: string
  name: string
  description?: string
  status: 'active'
  created_at: string
}
```

## PUT /api/workspaces/{id}

Update workspace information (future feature).

### Request
```typescript
PUT /api/workspaces/{id}
Content-Type: application/json

{
  "name": "Updated Workspace Name",
  "description": "Updated description",
  "tags": ["new-tag"]
}
```

### Response
```typescript
interface UpdateWorkspaceResponse {
  id: string
  name: string
  description?: string
  last_updated: string
}
```

## DELETE /api/workspaces/{id}

Delete a workspace (future feature).

### Request
```typescript
DELETE /api/workspaces/{id}
```

### Response
```typescript
interface DeleteWorkspaceResponse {
  id: string
  deleted_at: string
}
```