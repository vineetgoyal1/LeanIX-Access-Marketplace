---
name: leanix-graphql
description: Use LeanIX GraphQL API for querying and managing enterprise architecture data. Trigger this skill when you need to get providers from LeanIX, create or update fact sheets (Applications, Providers, ITComponents, etc.), search with filters, find data quality issues, manage relations, handle pagination, or perform any LeanIX data operations that benefit from precise field selection, complex filtering, or batch mutations. Use this for both direct API calls and when writing Python scripts that interact with LeanIX. Always prefer this skill over REST API for queries with filtering, fact sheet creation/updates, and batch operations.
---

# LeanIX GraphQL

## Overview

This skill enables you to work with the SAP LeanIX GraphQL API to query, create, update, and manage enterprise architecture data. LeanIX stores fact sheets (Applications, Providers, ITComponents, etc.) and their relationships. Use this skill whenever you need to interact with LeanIX data programmatically.

## When to Use GraphQL vs REST

**Use GraphQL (this skill) for:**
- Queries with specific field selection (fetch only what you need)
- Complex filtering with facets (quality, tags, lifecycle, etc.)
- Creating/updating fact sheets (uses mutations with JSON Patches)
- Managing relations between fact sheets
- Pagination through large datasets (cursor-based)
- Batch operations (multiple mutations with aliases - up to 50 per request)
- Data quality analysis (completion scores, missing fields)

**Use REST API for:**
- Simple single-record CRUD when GraphQL overhead isn't worth it
- File uploads
- Operations not well-supported in GraphQL
- Legacy integrations

**When in doubt, prefer GraphQL** - it's more flexible and efficient for most LeanIX operations.

## Critical Warnings

⚠️ **GraphiQL Node Limit**: The GraphiQL interface has a limit of **18,006 nodes**. For large workspaces, implement pagination with **max 1,000 fact sheets per page**.

⚠️ **Lifecycle Updates Are All-or-Nothing**: When updating lifecycle, you MUST include ALL phases or they will be deleted. See `references/advanced_examples.md#lifecycle-management`.

⚠️ **Batch Mutation Rollback**: If ONE mutation in a batch fails, ALL mutations fail (transaction rollback). Always validate data before batching.

⚠️ **GraphQL Always Returns HTTP 200**: Even on errors. MUST check `errors` field in response body.

⚠️ **Tag Filtering Uses IDs**: Must query `allTags` first to get tag IDs, can't filter by tag names directly.

⚠️ **externalId Format**: Must be JSON string: `{"type":"ExternalId","externalId":"value"}` - not a plain string.

## Core Concepts

### Authentication

LeanIX uses OAuth2 two-step authentication:

1. **Exchange API token for access token:**
```python
import requests

response = requests.post(
    f'https://{subdomain}.leanix.net/services/mtm/v1/oauth2/token',
    auth=("apitoken", LEANIX_API_TOKEN),
    data={"grant_type": "client_credentials"}
)
access_token = response.json()['access_token']
```

2. **Use access token for GraphQL requests:**
```python
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.post(
    f'https://{subdomain}.leanix.net/services/pathfinder/v1/graphql',
    headers=headers,
    data=json.dumps({'query': graphql_query, 'variables': variables})
)
```

**Security:** Always use environment variables for credentials, never hardcode them.

### GraphQL Request Structure

All GraphQL requests use HTTP POST with JSON body:

```python
{
    "query": "query or mutation string",
    "variables": {  # Optional but recommended
        "id": "some-id",
        "filter": {...}
    }
}
```

### Error Handling (CRITICAL)

**GraphQL always returns HTTP 200 OK, even on errors.** You MUST check the response body:

```python
response = requests.post(...)
result = response.json()

# ALWAYS check for GraphQL errors
if "errors" in result:
    # Handle error - mutations may have rolled back
    for error in result["errors"]:
        print(f"Error: {error['message']}")
        if "path" in error:
            print(f"Path: {error['path']}")
    raise Exception("GraphQL operation failed")

# Success
data = result["data"]
```

**Batch mutation rollback:** If you use mutation aliases to create 50 fact sheets and ONE has invalid data, ALL 50 fail (transaction rollback). Always validate data before batching.

## Common Operations

### 1. Query Fact Sheets

#### Get Single Fact Sheet by ID

```graphql
query ($id: ID!) {
  factSheet(id: $id) {
    id
    name
    type
    description
    completion {
      percentage
    }
    lxState
    ... on Provider {
      # Provider-specific fields
    }
    ... on Application {
      technicalSuitability
      functionalSuitability
    }
  }
}
```

Variables:
```json
{"id": "28fe4aa2-6e46-41a1-a131-72afb3acf256"}
```

**Key principle:** Request only the fields you need. GraphQL won't return fields you don't ask for.

#### Get All Fact Sheets with Filtering

```graphql
query ($filter: FilterInput!, $first: Int!, $cursor: String) {
  allFactSheets(
    filter: $filter,
    first: $first,
    after: $cursor
  ) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        displayName
        completion {
          percentage
        }
      }
    }
  }
}
```

Variables:
```json
{
  "filter": {
    "facetFilters": [
      {
        "facetKey": "FactSheetTypes",
        "operator": "OR",
        "keys": ["Provider"]
      },
      {
        "facetKey": "DataQuality",
        "operator": "OR",
        "keys": ["_noDescription_", "_noResponsible_"]
      }
    ]
  },
  "first": 100
}
```

**Pagination pattern:**
```python
all_results = []
cursor = None

while True:
    variables = {"filter": filter_obj, "first": 100}
    if cursor:
        variables["cursor"] = cursor

    response = execute_graphql(query, variables)

    if "errors" in response:
        raise Exception(f"Query failed: {response['errors']}")

    fact_sheets = response["data"]["allFactSheets"]
    all_results.extend([edge["node"] for edge in fact_sheets["edges"]])

    if not fact_sheets["pageInfo"]["hasNextPage"]:
        break

    cursor = fact_sheets["pageInfo"]["endCursor"]

return all_results
```

### 2. Filtering with Facets

**Global facet keys (all fact sheet types):**
- `FactSheetTypes`: Type (Application, Provider, ITComponent, etc.)
- `DataQuality`: noResponsible, qualitySealBroken, noDescription, noLifecycle
- `lxState`: BROKEN_QUALITY_SEAL, DRAFT, REJECTED, APPROVED
- `hierarchyLevel`: Hierarchy level
- `Subscriptions`: User subscriptions (filter by user ID, type, role)
- `TrashBin`: Archived status (use key "archived")
- `_TAGS_`: Tags (⚠️ **use tag IDs, not names** - query `allTags` first)

**Logical operators:**
- `OR`: At least one condition must be true (broadens results)
- `AND`: All conditions must be true (narrows results)
- `NOR`: None of the conditions can be true (excludes results)

**Example - Find incomplete providers:**
```json
{
  "filter": {
    "facetFilters": [
      {
        "facetKey": "FactSheetTypes",
        "operator": "OR",
        "keys": ["Provider"]
      },
      {
        "facetKey": "DataQuality",
        "operator": "OR",
        "keys": ["_noDescription_", "_noResponsible_"]
      }
    ]
  }
}
```

**Date filters (for lifecycle phases):**
```json
{
  "facetKey": "lifecycle",
  "operator": "OR",
  "keys": ["phaseIn"],
  "dateFilter": {
    "type": "RANGE",
    "from": "2023-01-01",
    "to": "2029-12-31"
  }
}
```

**Discovering available facets:**
```graphql
query {
  allFactSheets(factSheetType: Provider) {
    filterOptions {
      facets {
        facetKey
        possibleOperators
        results {
          name
          key
        }
      }
    }
  }
}
```

### 3. Create Fact Sheets

Uses `createFactSheet` mutation with JSON Patch operations:

```graphql
mutation ($input: BaseFactSheetInput!, $patches: [Patch]) {
  createFactSheet(input: $input, patches: $patches) {
    factSheet {
      id
      name
      type
      description
      ... on Application {
        externalId {
          externalId
        }
        alias
      }
    }
  }
}
```

Variables:
```json
{
  "input": {
    "name": "AC Management",
    "type": "Application"
  },
  "patches": [
    {
      "op": "add",
      "path": "/description",
      "value": "Application for AC management"
    },
    {
      "op": "add",
      "path": "/externalId",
      "value": "{\"type\":\"ExternalId\",\"externalId\":\"1234567890\"}"
    },
    {
      "op": "add",
      "path": "/alias",
      "value": "AC App"
    }
  ]
}
```

**JSON Patch operations:**
- `op: "add"` - Add new field or array element
- `op: "replace"` - Replace existing field value
- `op: "remove"` - Remove field or array element

**Path format:** `/fieldName` for simple fields, `/relationType/relationId` for relations

**Common fields:**
- `/description` - Fact sheet description
- `/externalId` - External system ID (JSON string format required)
- `/alias` - Alternative name for full-text search
- `/lxState` - Quality seal state (APPROVED, DRAFT, REJECTED, BROKEN_QUALITY_SEAL)

### 4. Update Fact Sheets

```graphql
mutation ($id: ID!, $patches: [Patch]!) {
  updateFactSheet(id: $id, patches: $patches) {
    factSheet {
      id
      description
    }
  }
}
```

Variables:
```json
{
  "id": "fact-sheet-id",
  "patches": [
    {
      "op": "replace",
      "path": "/description",
      "value": "Updated description"
    }
  ]
}
```

**Advantages over REST:**
- Update only the fields you want to change
- No need to pass unchanged fields
- More granular control

### 5. Batch Operations with Mutation Aliases

Create multiple fact sheets in ONE request (up to ~50 recommended):

```graphql
mutation {
  p1: createFactSheet(
    input: {name: "Provider 1", type: Provider}
    patches: [{op: add, path: "/description", value: "First provider"}]
  ) {
    factSheet { id name }
  },
  p2: createFactSheet(
    input: {name: "Provider 2", type: Provider}
    patches: [{op: add, path: "/description", value: "Second provider"}]
  ) {
    factSheet { id name }
  }
}
```

**CRITICAL batch behavior:**
- ONE invalid mutation = ALL mutations fail (transaction rollback)
- Validate all data BEFORE batching
- Consider fallback to individual creation on batch failure

**Python pattern:**
```python
def create_providers_batch(providers):
    # Validate ALL providers first
    for provider in providers:
        validate_provider_data(provider)

    # Build mutation with aliases
    mutations = []
    for i, provider in enumerate(providers):
        mutations.append(f"""
            p{i}: createFactSheet(
                input: {{name: "{provider['name']}", type: Provider}},
                patches: [{{op: add, path: "/description", value: "{provider['description']}"}}]
            ) {{
                factSheet {{ id name }}
            }}
        """)

    full_mutation = f"mutation {{ {','.join(mutations)} }}"

    response = execute_graphql(full_mutation)

    # Check for errors
    if "errors" in response:
        # ALL failed - try individually
        return create_providers_individually(providers)

    return response["data"]
```

### 6. Manage Relations

**Create relation:**
```graphql
mutation {
  updateFactSheet(id: "source-id", patches: [
    {
      op: add,
      path: "/relToSuccessor/new_source-id",
      value: "{\"factSheetId\":\"target-id\",\"activeFrom\":\"2023-11-29\",\"activeUntil\":\"2024-11-29\"}"
    }
  ]) {
    factSheet {
      id
      ... on Application {
        relToSuccessor {
          edges {
            node {
              id
              factSheet { id name }
            }
          }
        }
      }
    }
  }
}
```

**Key points:**
- Path format: `/relationType/new_{id}` for creating (use "new_" prefix)
- Value is a **JSON string** (not a JSON object) - escape quotes
- Use actual relationId for updating: `/relationType/{relationId}`

**Update relation:**
```graphql
{
  op: replace,
  path: "/relToSuccessor/{relationId}",
  value: "{\"factSheetId\":\"target-id\",\"activeFrom\":\"2024-01-01\"}"
}
```

**Delete relation:**
```graphql
{
  op: remove,
  path: "/relToSuccessor/{relationId}",
  value: ""
}
```

### 7. Type-Specific Fields

Use GraphQL fragments for type-specific fields:

```graphql
query {
  factSheet(id: "some-id") {
    id
    name
    type
    ... on Application {
      technicalSuitability
      functionalSuitability
      lifecycle {
        phases {
          phase
          startDate
        }
      }
    }
    ... on Provider {
      # Provider-specific fields
    }
  }
}
```

### 8. Archive (Soft Delete)

```graphql
mutation {
  updateFactSheet(
    id: "fact-sheet-id",
    comment: "Archive reason",
    patches: [{
      op: add,
      path: "/status",
      value: "ARCHIVED"
    }]
  ) {
    factSheet {
      id
      status
    }
  }
}
```

## Python Implementation Patterns

### Complete Example: Create Provider

```python
import os
import requests
import json

LEANIX_API_TOKEN = os.getenv('LEANIX_API_TOKEN')
LEANIX_SUBDOMAIN = os.getenv('LEANIX_SUBDOMAIN')
LEANIX_GRAPHQL_URL = f'https://{LEANIX_SUBDOMAIN}.leanix.net/services/pathfinder/v1/graphql'
LEANIX_OAUTH2_URL = f'https://{LEANIX_SUBDOMAIN}.leanix.net/services/mtm/v1/oauth2/token'

def obtain_access_token() -> str:
    """Get access token via OAuth2"""
    if not LEANIX_API_TOKEN:
        raise Exception('LEANIX_API_TOKEN environment variable required')

    response = requests.post(
        LEANIX_OAUTH2_URL,
        auth=("apitoken", LEANIX_API_TOKEN),
        data={"grant_type": "client_credentials"}
    )
    response.raise_for_status()
    return response.json()['access_token']

def execute_graphql(query: str, variables: dict = None) -> dict:
    """Execute GraphQL query/mutation"""
    access_token = obtain_access_token()

    data = {'query': query}
    if variables:
        data['variables'] = variables

    response = requests.post(
        url=LEANIX_GRAPHQL_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        data=json.dumps(data)
    )
    response.raise_for_status()
    result = response.json()

    # CRITICAL: Check for GraphQL errors
    if "errors" in result:
        raise Exception(f"GraphQL errors: {result['errors']}")

    return result

def create_provider(name: str, description: str) -> dict:
    """Create a Provider fact sheet"""
    mutation = """
        mutation ($input: BaseFactSheetInput!, $patches: [Patch]) {
            createFactSheet(input: $input, patches: $patches) {
                factSheet {
                    id
                    name
                    type
                    description
                }
            }
        }
    """

    variables = {
        "input": {
            "name": name,
            "type": "Provider"
        },
        "patches": [
            {
                "op": "add",
                "path": "/description",
                "value": description
            }
        ]
    }

    result = execute_graphql(mutation, variables)
    return result["data"]["createFactSheet"]["factSheet"]

# Usage
provider = create_provider("Test Provider", "A test provider")
print(f"Created provider: {provider['id']}")
```

### Complete Example: Query with Pagination and Filtering

```python
def get_incomplete_providers() -> list:
    """Get all providers missing descriptions or responsible persons"""
    query = """
        query ($filter: FilterInput!, $first: Int!, $cursor: String) {
            allFactSheets(
                filter: $filter,
                first: $first,
                after: $cursor
            ) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                        displayName
                        completion {
                            percentage
                        }
                        lxState
                    }
                }
            }
        }
    """

    variables = {
        "filter": {
            "facetFilters": [
                {
                    "facetKey": "FactSheetTypes",
                    "operator": "OR",
                    "keys": ["Provider"]
                },
                {
                    "facetKey": "DataQuality",
                    "operator": "OR",
                    "keys": ["_noDescription_", "_noResponsible_"]
                }
            ]
        },
        "first": 100
    }

    all_providers = []
    cursor = None

    while True:
        if cursor:
            variables["cursor"] = cursor

        result = execute_graphql(query, variables)
        fact_sheets = result["data"]["allFactSheets"]

        all_providers.extend([edge["node"] for edge in fact_sheets["edges"]])

        if not fact_sheets["pageInfo"]["hasNextPage"]:
            break

        cursor = fact_sheets["pageInfo"]["endCursor"]

    return all_providers

# Usage
providers = get_incomplete_providers()
print(f"Found {len(providers)} incomplete providers")
for p in providers:
    print(f"- {p['displayName']}: {p['completion']['percentage']}% complete")
```

## GraphiQL Tool (Interactive Testing)

**Access:** Help menu → Developer Tools → GraphQL Editor

**Features:**
- Interactive query editor with syntax highlighting
- Schema documentation browser (click "Show Documentation Explorer")
- Query history
- Visual query builder (click "Show GraphiQL Explorer")
- Test queries/mutations before implementing in code

**Export from Inventory:**
- Apply filters in LeanIX inventory
- Click arrow icon on filter bar → "Copy as JSON Query" or "Open in GraphiQL"
- Saves time on complex filter configurations

**Admin access required by default** - can be granted to other roles in User Roles and Permissions.

## Best Practices

1. **Request only needed fields** - Reduces payload size and improves performance
2. **Use variables instead of string interpolation** - Safer and prevents injection-like issues
3. **Always check for errors in response body** - HTTP 200 doesn't mean success
4. **Use pagination for large datasets** - Default page size: 100 items
5. **Validate before batching** - One error fails all mutations in a batch
6. **Use mutation aliases for bulk operations** - But chunk into ~50 per request
7. **Prefer GraphQL for complex queries** - REST for simple single-record operations
8. **Use environment variables for credentials** - Never hardcode tokens
9. **Check user_notes in transcripts** - May reveal issues that assertions miss
10. **Leverage facet filtering** - More efficient than loading all data and filtering locally

## Common Pitfalls

❌ **Assuming HTTP 200 means success** - Always check `errors` field in response body
❌ **Not validating before batch mutations** - One error rolls back all 50 mutations
❌ **Using string interpolation for queries** - Use variables instead
❌ **Forgetting pagination** - Will only get first 100 results (GraphiQL: max 1,000/page)
❌ **Requesting all fields when you need few** - Increases payload and latency
❌ **Using wrong relation path format** - Use `/relType/new_{id}` for create, `/relType/{relationId}` for update
❌ **Passing JSON object as relation value** - Must be JSON string with escaped quotes
❌ **Ignoring completion score fields** - Important for data quality tracking
❌ **Not handling transaction rollback** - Need fallback when batch fails
❌ **Using tag names in filters** - Must use tag IDs (query `allTags` first)
❌ **Wrong externalId format** - Must be `{"type":"ExternalId","externalId":"value"}` string
❌ **Partial lifecycle updates** - Must include ALL phases or they get deleted
❌ **Not using naFields for intentionally empty** - Misses opportunity to improve completion score
❌ **Filtering by external ID incorrectly** - Use format: `externalIds: ["externalId/value"]`

## Reference Documentation

For more details, see:
- `references/advanced_examples.md` - **External IDs, aliases, lifecycle, quality seal, naFields, tags, subscriptions, archived fact sheets, relation validity, event logs, custom attributes**
- `references/facets_reference.md` - All available facet keys by fact sheet type
- `references/error_codes.md` - Common error messages and solutions
- `scripts/leanix_client.py` - Reusable Python client module

**When to consult advanced_examples.md:**
- Working with external IDs or aliases
- Managing lifecycle phases
- Setting quality seals
- Marking fields as intentionally empty (naFields)
- Filtering by tags (need tag IDs)
- Filtering by subscriptions (user/role)
- Working with archived fact sheets
- Filtering relations by field values
- Filtering by relation validity (activeFrom/activeUntil)
- Retrieving event logs (audit trail)
- Updating custom attributes

## When NOT to Use This Skill

- Simple file operations (use file tools instead)
- Non-LeanIX API interactions (use appropriate tools)
- When REST API is explicitly required (wait for leanix-rest skill)
- When LeanIX MCP tools are simpler and sufficient (e.g., single fact sheet retrieval)
