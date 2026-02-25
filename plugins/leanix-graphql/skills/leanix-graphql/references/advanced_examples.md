# Advanced LeanIX GraphQL Examples

## Table of Contents
1. [External IDs](#external-ids)
2. [Aliases](#aliases)
3. [Lifecycle Management](#lifecycle-management)
4. [Quality Seal](#quality-seal)
5. [Intentionally Empty Fields (naFields)](#intentionally-empty-fields)
6. [Tag Filtering](#tag-filtering)
7. [Subscription Filtering](#subscription-filtering)
8. [Archived Fact Sheets](#archived-fact-sheets)
9. [Relation Field Filtering](#relation-field-filtering)
10. [Relation Validity](#relation-validity)
11. [Event Logs](#event-logs)
12. [Custom Attributes](#custom-attributes)

---

## External IDs

External IDs link fact sheets to records in external systems.

### Format

External IDs must be JSON strings with specific structure:
```json
{"type":"ExternalId","externalId":"actual-id-value"}
```

### Creating with External ID

```graphql
mutation ($input: BaseFactSheetInput!, $patches: [Patch]!) {
  createFactSheet(input: $input, patches: $patches) {
    factSheet {
      id
      name
      ... on Application {
        externalId {
          externalId
        }
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
      "path": "/externalId",
      "value": "{\"type\":\"ExternalId\",\"externalId\":\"1234567890\"}"
    }
  ]
}
```

### Updating External ID

```graphql
mutation ($patches: [Patch]!) {
  updateFactSheet(id: "fact-sheet-id", patches: $patches) {
    factSheet {
      ... on Application {
        externalId {
          externalId
        }
      }
    }
  }
}
```

Variables:
```json
{
  "patches": [
    {
      "op": "replace",
      "path": "/externalId",
      "value": "{\"type\":\"ExternalId\",\"externalId\":\"new-id\"}"
    }
  ]
}
```

### Deleting External ID

```json
{
  "patches": [
    {
      "op": "remove",
      "path": "/externalId",
      "value": ""
    }
  ]
}
```

### Filtering by External ID

Special format: `externalIds: ["externalId/value"]`

```graphql
{
  allFactSheets(filter: {externalIds: ["externalId/1234"]}) {
    edges {
      node {
        id
        name
        ... on Application {
          externalId {
            externalId
          }
        }
      }
    }
  }
}
```

---

## Aliases

Aliases are alternative names used in full-text search.

### Adding Alias

```graphql
mutation ($patches: [Patch]!) {
  createFactSheet(
    input: {name: "AC Management", type: Application}
    patches: $patches
  ) {
    factSheet {
      ... on Application {
        alias
      }
    }
  }
}
```

Variables:
```json
{
  "patches": [
    {
      "op": "add",
      "path": "/alias",
      "value": "AC App"
    }
  ]
}
```

---

## Lifecycle Management

### CRITICAL WARNING: All-or-Nothing Updates

**When updating lifecycle, you MUST include ALL phases or they will be deleted.**

If you only include `plan` phase, all other phases are deleted. The `remove` operation deletes ALL phases regardless of input.

### Update Lifecycle (Correct Way)

```graphql
mutation ($patches: [Patch]!) {
  updateFactSheet(id: "fact-sheet-id", patches: $patches) {
    factSheet {
      ... on Initiative {
        lifecycle {
          phases {
            phase
            startDate
          }
        }
      }
    }
  }
}
```

Variables - **Must include ALL phases:**
```json
{
  "patches": [
    {
      "op": "replace",
      "path": "/lifecycle",
      "value": "{\"phases\":[{\"phase\":\"plan\",\"startDate\":\"2019-01-12\"},{\"phase\":\"phaseIn\",\"startDate\":\"2020-03-12\"},{\"phase\":\"active\",\"startDate\":\"2021-05-10\"},{\"phase\":\"phaseOut\",\"startDate\":\"2025-03-30\"},{\"phase\":\"endOfLife\",\"startDate\":\"2027-01-01\"}]}"
    }
  ]
}
```

### Lifecycle Phase Names

- `plan`
- `phaseIn`
- `active`
- `phaseOut`
- `endOfLife`

---

## Quality Seal

### Setting Quality Seal to APPROVED

```graphql
mutation ($patches: [Patch]!) {
  updateFactSheet(id: "fact-sheet-id", patches: $patches) {
    factSheet {
      lxState
    }
  }
}
```

Variables:
```json
{
  "patches": [
    {
      "op": "replace",
      "path": "/lxState",
      "value": "APPROVED"
    }
  ]
}
```

### Quality Seal States

- `APPROVED` - Quality seal approved
- `DRAFT` - Draft state
- `REJECTED` - Quality seal rejected
- `BROKEN_QUALITY_SEAL` - Quality seal broken

---

## Intentionally Empty Fields

Use `naFields` to mark fields as intentionally empty (not missing data). This **affects completion score** - intentionally empty fields count as complete.

### Setting Empty Relation

```graphql
mutation ($patches: [Patch]!) {
  updateFactSheet(id: "fact-sheet-id", patches: $patches) {
    factSheet {
      naFields
    }
  }
}
```

Variables:
```json
{
  "patches": [
    {
      "op": "add",
      "path": "/naFields",
      "value": "[\"relToParent\"]"
    }
  ]
}
```

**Use case:** Application has no parent - mark `relToParent` as intentionally empty to improve completion score.

---

## Tag Filtering

### IMPORTANT: Tags use IDs, not names

First, get tag IDs:

```graphql
{
  allTags {
    edges {
      node {
        id
        name
        tagGroup {
          id
          name
        }
      }
    }
  }
}
```

### Filter by Tags (Multiple Tags with AND)

```graphql
query ($filter: FilterInput!, $sortings: [Sorting]) {
  allFactSheets(filter: $filter, sort: $sortings) {
    edges {
      node {
        id
        displayName
        tags {
          id
          name
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
        "keys": ["Platform"]
      },
      {
        "facetKey": "_TAGS_",
        "operator": "AND",
        "keys": [
          "6c8d1073-0724-4582-97bd-c972e85be0cb",
          "1c9c71b0-db60-453e-b607-05471c4f839a"
        ]
      }
    ]
  },
  "sortings": [
    {
      "key": "updatedAt",
      "order": "desc"
    }
  ]
}
```

**Key points:**
- Use tag IDs in `keys` array
- `_TAGS_` searches across all tag groups
- To filter specific tag group: use tag group ID as facetKey instead of `_TAGS_`
- `AND` operator: fact sheet must have ALL tags
- `OR` operator: fact sheet must have AT LEAST ONE tag

### Get Tag Group IDs

```graphql
{
  allTagGroups {
    edges {
      node {
        id
        name
        shortName
      }
    }
  }
}
```

---

## Subscription Filtering

Filter fact sheets by who is subscribed and their role.

### Get User ID

Your user ID: Admin area → API Tokens → look for UserId

All workspace users: GET request to MTM REST API:
```
https://{subdomain}.leanix.net/services/mtm/v1/workspaces/{id}/users
```

### Get Subscription Role IDs

```graphql
{
  allSubscriptionRoles {
    edges {
      node {
        id
        name
      }
    }
  }
}
```

### Filter by Subscription

```graphql
query ($filter: FilterInput!) {
  allFactSheets(filter: $filter) {
    totalCount
    edges {
      node {
        id
        displayName
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
        "keys": ["Application"]
      },
      {
        "facetKey": "Subscriptions",
        "operator": "OR",
        "keys": ["87678c21-98a2-9567-acaa-fc66ff2b9d56"],
        "subscriptionFilter": {
          "type": "ACCOUNTABLE",
          "roleId": "a523b819-208c-49ef-a0c6-8d8b84464f6e"
        }
      }
    ]
  }
}
```

**Subscription types:**
- `ACCOUNTABLE` - Accountable for fact sheet
- `RESPONSIBLE` - Responsible for fact sheet
- `OBSERVER` - Observer of fact sheet

---

## Archived Fact Sheets

### Archive Fact Sheet

```graphql
mutation ($patches: [Patch]!) {
  updateFactSheet(
    id: "fact-sheet-id",
    comment: "Irrelevant application",
    patches: $patches
  ) {
    factSheet {
      status
    }
  }
}
```

Variables:
```json
{
  "patches": [
    {
      "op": "add",
      "path": "/status",
      "value": "ARCHIVED"
    }
  ]
}
```

### Recover Archived Fact Sheet

```json
{
  "patches": [
    {
      "op": "add",
      "path": "/status",
      "value": "ACTIVE"
    }
  ]
}
```

### Filter Archived Fact Sheets

```graphql
query ($filter: FilterInput!) {
  allFactSheets(filter: $filter) {
    edges {
      node {
        id
        name
        status
      }
    }
  }
}
```

Variables:
```json
{
  "filter": {
    "responseOptions": {
      "maxFacetDepth": 5
    },
    "facetFilters": [
      {
        "facetKey": "TrashBin",
        "operator": "OR",
        "keys": ["archived"]
      }
    ]
  }
}
```

---

## Relation Field Filtering

Filter fact sheets by specific relation field values (e.g., support type).

### Example: Applications with Leading Support Type

```graphql
query ($filter: FilterInput!) {
  allFactSheets(filter: $filter) {
    edges {
      node {
        id
        displayName
        ... on Application {
          relApplicationToBusinessCapability {
            edges {
              node {
                supportType
                factSheet {
                  id
                  name
                }
              }
            }
          }
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
        "keys": ["Application"]
      },
      {
        "facetKey": "relApplicationToBusinessCapability",
        "operator": "OR",
        "keys": [
          "5634544d-4cd3-4533-b190-3f947a99e752",
          "0c53c875-feab-4a87-9006-c0b3191aa65f"
        ],
        "relationFieldsFilterOperator": "INCLUSIVE",
        "relationFieldsFilter": [
          {
            "fieldName": "supportType",
            "values": ["leading"]
          }
        ]
      }
    ]
  }
}
```

**Key points:**
- `relationFieldsFilterOperator: "INCLUSIVE"` - return only relations matching the filter
- `relationFieldsFilter` - array of field filters
- `keys` in facet filter = target fact sheet IDs

---

## Relation Validity

Relations have validity periods (activeFrom/activeUntil). Filter relations by date ranges.

### Filter Relations by Validity in Facets

```graphql
{
  allFactSheets(filter: {
    facetFilters: [
      {facetKey: "FactSheetTypes", keys: ["UserGroup"]},
      {facetKey: "relUserGroupToApplication", keys: ["app-id"]},
      {
        facetKey: "lifecycle",
        keys: "__any__",
        dateFilter: {
          type: RANGE,
          from: "2018-07-01",
          to: "2018-07-31"
        }
      }
    ]
  }) {
    edges {
      node {
        displayName
      }
    }
  }
}
```

**Note:** Currently uses lifecycle facet dateFilter for relation validity (will change in future).

### Filter Relations by Validity on Fact Sheet

```graphql
{
  factSheet(id: "app-id") {
    displayName
    ... on Application {
      relApplicationToUserGroup(
        validityFilter: {
          activeFrom: "2018-07-01",
          activeUntil: "2018-07-31"
        }
      ) {
        edges {
          node {
            activeFrom
            activeUntil
            factSheet {
              displayName
            }
          }
        }
      }
    }
  }
}
```

**Date filter types:**
- `RANGE` - Date range (from/to)
- `POINT` - Single date (from only, to ignored)
- `TODAY` - Today (from/to ignored)
- `END_OF_MONTH` - End of current month
- `END_OF_YEAR` - End of current year

**Matching logic:** Relation matches if validity interval overlaps with filter interval (non-empty intersection).

---

## Event Logs

Retrieve audit trail for fact sheet changes.

### Query Event Logs

```graphql
{
  allLogEvents(
    factSheetId: "fact-sheet-id"
    eventTypes: QUALITY_SEAL_APPROVED
  ) {
    edges {
      node {
        id
        eventType
        path
        oldValue
        newValue
        message
        secondsPast
        createdAt
        user {
          id
          displayName
          email
          technicalUser
        }
      }
    }
  }
}
```

**Event types** (find more in GraphiQL schema):
- `QUALITY_SEAL_APPROVED`
- `FACT_SHEET_TAG_ADDED`
- `FACT_SHEET_TAG_REMOVED`
- `FACT_SHEET_CREATED`
- `FACT_SHEET_UPDATED`
- `FACT_SHEET_ARCHIVED`

**Use cases:**
- Track quality seal expiration (3 months from `createdAt`)
- Audit trail for compliance
- Monitor fact sheet changes
- Identify who made changes

**Automation tip:** Loop through all fact sheet IDs (from `allFactSheets`) to fetch logs for multiple fact sheets.

---

## Custom Attributes

Custom attributes use attribute IDs (not names) in path.

### Find Attribute ID

Navigate to fact sheet configuration in LeanIX UI → find attribute key

### Update Custom Attribute

```graphql
mutation ($patches: [Patch]!) {
  updateFactSheet(id: "fact-sheet-id", patches: $patches) {
    factSheet {
      ... on Application {
        serviceNowId
      }
    }
  }
}
```

Variables:
```json
{
  "patches": [
    {
      "op": "replace",
      "path": "/serviceNowId",
      "value": "SN-123456"
    }
  ]
}
```

### Multiple Select Custom Attribute

Value must be JSON array string:

```json
{
  "patches": [
    {
      "op": "replace",
      "path": "/supportedPlatforms",
      "value": "[\"macOS\", \"windows\"]"
    }
  ]
}
```

---

## Summary

These advanced patterns enable:
- External system integration (externalId)
- Search optimization (alias)
- Complex date-based filtering (lifecycle, relation validity)
- Data quality management (quality seal, naFields, completion score)
- Access control filtering (subscriptions)
- Audit trails (event logs)
- Tag-based categorization
- Workspace-specific customization (custom attributes)
