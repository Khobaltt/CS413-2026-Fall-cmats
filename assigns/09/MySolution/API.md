# LAMBDA-studio storage API v1

The base URL is `http://127.0.0.1:9000/api/v1`. Send UTF-8 JSON with
`Content-Type: application/json` for requests with a body. Reads and
successful writes return JSON. HEAD is also available on GET routes and
returns headers without a body. Top-level deletes return an empty 204 response.
The API stores LAMBDA source as text. The studio sends saved test sources
separately to the Assign07 LAMBDA3 service. See [openapi.json](openapi.json)
for machine-readable request and response schemas.

| Method and path relative to base | Request | Successful response |
| --- | --- | --- |
| GET /health | none | 200 `{"status":"ok","version":"1.0"}` |
| POST /programs | Program input | 201 `{"program": Program}` and ETag |
| GET /programs | `limit`, `cursor` | 200 `{"items":[Program, ...],"next_cursor":string or null}` |
| GET /programs/{id} | none | 200 `{"program": Program}` and ETag |
| PUT /programs/{id} | Program input and If-Match | 200 `{"program": Program}` and ETag |
| DELETE /programs/{id} | If-Match | 204 |
| POST /collections | Collection input | 201 `{"collection": Collection}` and ETag |
| GET /collections | `limit`, `cursor` | 200 `{"items":[Collection, ...],"next_cursor":string or null}` |
| GET /collections/{id} | none | 200 `{"collection": Collection}` and ETag |
| PUT /collections/{id} | Collection input and If-Match | 200 `{"collection": Collection}` and ETag |
| DELETE /collections/{id} | If-Match | 204 |
| POST /collections/{id}/cases | Case input and collection If-Match | 201 `{"collection": Collection}` and ETag |
| PUT /collections/{id}/cases/{case_id} | Case input and collection If-Match | 200 `{"collection": Collection}` and ETag |
| DELETE /collections/{id}/cases/{case_id} | Collection If-Match | 200 `{"collection": Collection}` and ETag |

## Records and validation

| Record | Write fields | Additional response fields |
| --- | --- | --- |
| Program | `name`, `source`, optional `description` | `id`, `created_at`, `updated_at`, `revision` |
| Collection | `name`, optional `description` | `id`, `created_at`, `updated_at`, `revision`, ordered `cases` |
| Case | `name`, `source`, `expected`, optional `description` | `id` |

Fields are strings except `revision` (positive integer), `expected` (tagged
object), and `cases` (array of full case records). Timestamps are UTC ISO
8601. IDs are service-generated opaque strings. Path IDs accept 1–64 ASCII
letters, digits, underscores, or hyphens. Descriptions default to the empty
string on each write. Unknown fields, duplicate JSON keys, and invalid Unicode
are rejected. Source must contain a non-whitespace character and is stored
verbatim. Names are trimmed and must be nonempty. Name uniqueness is
case-sensitive and scoped to programs, collections, or cases in one collection.

The exact allowed expectation shapes are
`{"kind":"value","value":"42"}`, `{"kind":"error","category":"syntax"}`,
and `{"kind":"error","category":"type"}`. Value matching compares the
formatted LAMBDA3 value as a string. Only the corresponding LAMBDA3
syntax or type error satisfies an error expectation.

| Limit | Maximum |
| --- | --- |
| Name after trimming | 120 Unicode characters |
| Source | 16,384 UTF-8 bytes |
| Description | 2,000 Unicode characters |
| Expected formatted value | 16,384 UTF-8 bytes |
| Raw HTTP request body | 524,288 bytes |
| Page size | 100 records, default 50 |
| Cases per collection | 25 |
| Total programs, collections, and cases combined | 100 |
| Distinct retained pagination snapshots | 64 |

## Revisions and pagination

New programs and collections start at revision 1. An item response that
returns a revision after a create, get, or mutation sends that revision
as a strong quoted ETag, such as `"1"`. PUT and DELETE require the exact
current ETag in `If-Match`. Case mutations use the collection tag.
A successful update increases that revision by one and updates the timestamp.
Updating collection metadata preserves its case order. Case creation appends
to the collection, and case updates preserve position and ID. Deleting a
collection deletes its cases. A program's deletion has no effect on test
case source snapshots. Lookups, revision checks, and changes run as one
atomic operation. A missing valid record ID is reported before precondition
validation, including a missing case in an existing collection.

List results are ordered by insertion. The first page captures the full
ordered record representations, including collection cases. The service
retains that snapshot only if another page is needed and reuses it for
identical first-page result sets. Random opaque tokens identify a snapshot's
resource and position. A later page can supply a different valid limit.
Tokens can be replayed and remain valid until service restart. Every page
uses the captured representations, even after changes and deletions. A
cursor from another resource or process returns 400. If retention is full,
starting another distinct multi-page snapshot returns 409. Single-page
requests and existing cursor chains can still proceed. Query parameters
may appear once and are accepted only on the two list routes.

The database and cursor state live in memory and are cleared when the
service process stops.

## Errors

Every error has a JSON body with the shape
`{"error":{"code":"invalid_request","message":"..."}}`.
Revision conflicts also include `current_revision` inside `error`.

| HTTP status | Code | Condition |
| --- | --- | --- |
| 400 | `invalid_request` | malformed JSON, invalid fields, query, path IDs or ETags |
| 404 | `record_not_found` | unknown record or route |
| 405 | `method_not_allowed` | unsupported method on a known route, with Allow header |
| 409 | `duplicate_name` | existing name in the same scope |
| 409 | `revision_conflict` | a valid but stale If-Match |
| 409 | `capacity_limit` | a record, case, or snapshot capacity is reached |
| 413 | `request_too_large` | oversized HTTP body |
| 415 | `unsupported_media_type` | wrong content type for a JSON body |
| 428 | `precondition_required` | missing If-Match for an existing record |
| 500 | `internal_error` | unexpected server failure |

## HTTP examples

Examples use a short illustrative opaque ID and abbreviate repetitive headers.

```http
POST /api/v1/programs
Content-Type: application/json

{"name":"Arithmetic","source":"6 * 7"}

HTTP/1.1 201 Created
ETag: "1"
Content-Type: application/json

{"program":{"id":"example","name":"Arithmetic","source":"6 * 7","description":"","created_at":"2026-11-22T18:00:00+00:00","updated_at":"2026-11-22T18:00:00+00:00","revision":1}}
```

```http
GET /api/v1/programs?limit=1

HTTP/1.1 200 OK
Content-Type: application/json

{"items":[{"id":"example","name":"Arithmetic","source":"6 * 7","description":"","created_at":"2026-11-22T18:00:00+00:00","updated_at":"2026-11-22T18:00:00+00:00","revision":1}],"next_cursor":null}
```

```http
GET /api/v1/programs/example

HTTP/1.1 200 OK
ETag: "1"
Content-Type: application/json

{"program":{"id":"example","name":"Arithmetic","source":"6 * 7","description":"","created_at":"2026-11-22T18:00:00+00:00","updated_at":"2026-11-22T18:00:00+00:00","revision":1}}
```

```http
PUT /api/v1/programs/example
Content-Type: application/json
If-Match: "1"

{"name":"Arithmetic","source":"7 * 7"}

HTTP/1.1 200 OK
ETag: "2"
Content-Type: application/json

{"program":{"id":"example","name":"Arithmetic","source":"7 * 7","description":"","created_at":"2026-11-22T18:00:00+00:00","updated_at":"2026-11-22T18:01:00+00:00","revision":2}}
```

```http
DELETE /api/v1/programs/example
If-Match: "1"

HTTP/1.1 409 Conflict
Content-Type: application/json

{"error":{"code":"revision_conflict","message":"The record has changed.","current_revision":2}}
```

```http
DELETE /api/v1/programs/example
If-Match: "2"

HTTP/1.1 204 No Content
```

```http
GET /api/v1/collections?limit=0

HTTP/1.1 400 Bad Request
Content-Type: application/json

{"error":{"code":"invalid_request","message":"limit must be an integer from 1 to 100."}}
```
