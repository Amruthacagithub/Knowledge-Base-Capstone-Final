# API Documentation — TechNova Platform API v2

## Overview

The TechNova Platform API is a RESTful service that powers our core product. All endpoints use JSON for request and response bodies. Authentication is required for all endpoints.

## Base URL

```
Production: https://api.technova.com/v2
Staging:    https://api-staging.technova.com/v2
```

## Authentication

All requests must include an API key in the header:

```
Authorization: Bearer <your-api-key>
```

API keys can be generated in the Developer Portal under Settings > API Keys.

## Endpoints

### GET /users

Returns a list of all users in the organization.

**Query Parameters:**
- `page` (int, default: 1) — Page number
- `limit` (int, default: 20, max: 100) — Results per page
- `department` (string, optional) — Filter by department

**Response:**
```json
{
  "data": [
    {"id": "u-123", "name": "Alice Smith", "department": "engineering", "role": "senior_engineer"}
  ],
  "pagination": {"page": 1, "total_pages": 5, "total_items": 95}
}
```

### POST /documents/upload

Upload a new document to the knowledge base.

**Request Body (multipart/form-data):**
- `file` (required) — The document file (PDF, MD, or JSON)
- `department` (required) — Department tag
- `classification` (required) — "public" or "restricted"

**Response:**
```json
{"id": "doc-456", "status": "processing", "message": "Document queued for indexing"}
```

### GET /search

Search across the knowledge base.

**Query Parameters:**
- `q` (string, required) — Search query
- `department` (string, optional) — Filter by department
- `limit` (int, default: 10) — Number of results

**Response:**
```json
{
  "results": [
    {"doc_id": "doc-789", "title": "PTO Policy", "snippet": "All employees receive 20 days...", "score": 0.92}
  ],
  "total": 15
}
```

## Rate Limits

- Standard tier: 100 requests per minute
- Enterprise tier: 1,000 requests per minute

Exceeding the rate limit returns HTTP 429 with a `Retry-After` header.

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request — check your parameters |
| 401 | Unauthorized — invalid or missing API key |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource doesn't exist |
| 429 | Rate Limited — slow down |
| 500 | Internal Server Error — contact support |
