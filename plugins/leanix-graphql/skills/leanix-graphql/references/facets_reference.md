# LeanIX GraphQL Facets Reference

## Global Facet Keys (All Fact Sheet Types)

These facets apply to all fact sheet types:

| Facet Key | Description | Possible Values | Operators |
|-----------|-------------|-----------------|-----------|
| `FactSheetTypes` | Fact sheet type | Application, Provider, ITComponent, BusinessCapability, Process, UserGroup, Project, Interface, DataObject, TechnicalStack, Objective, Platform, Initiative, BusinessContext, Organization | OR |
| `DataQuality` | Data quality issues | `_noResponsible_`, `_qualitySealBroken_`, `_noDescription_`, `_noLifecycle_` | OR, AND, NOR |
| `lxState` | Quality seal state | BROKEN_QUALITY_SEAL, DRAFT, REJECTED, APPROVED | OR, NOR |
| `hierarchyLevel` | Hierarchy level | 1, 2, 3, ... | OR |
| `Subscriptions` | User subscriptions | (user IDs) | OR |
| `TrashBin` | Trash bin status | (boolean filter) | OR |
| `_TAGS_` | Tags | (tag IDs and names) | OR |

## Application-Specific Facets

| Facet Key | Description | Possible Values | Operators |
|-----------|-------------|-----------------|-----------|
| `technicalSuitability` | Technical fit | perfect, appropriate, adequate, insufficient, unreasonable | OR, NOR |
| `functionalSuitability` | Functional fit | perfect, appropriate, adequate, insufficient, unreasonable | OR, NOR |
| `lifecycle` | Lifecycle phase | plan, phaseIn, active, phaseOut, endOfLife | OR |

## Provider-Specific Facets

(To be discovered via schema introspection - Provider facets may include category, type, etc.)

## ITComponent-Specific Facets

| Facet Key | Description | Possible Values | Operators |
|-----------|-------------|-----------------|-----------|
| `technicalSuitability` | Technical fit | (same as Application) | OR, NOR |

## Interface-Specific Facets

| Facet Key | Description | Possible Values | Operators |
|-----------|-------------|-----------------|-----------|
| `dataFlowDirection` | Data flow direction | inbound, outbound, bidirectional | OR |

## Discovering Available Facets

To find all facets for a specific fact sheet type:

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
        dateFilter {
          type
          minDate
          maxDate
        }
      }
    }
  }
}
```

Response includes:
- `facetKey`: The key to use in filters
- `possibleOperators`: Valid operators for this facet (OR, AND, NOR)
- `results`: Available values with names and keys
- `dateFilter`: If the facet supports date ranges

## Filter Construction Examples

### Single Facet Filter

```json
{
  "filter": {
    "facetFilters": [
      {
        "facetKey": "FactSheetTypes",
        "operator": "OR",
        "keys": ["Application"]
      }
    ]
  }
}
```

### Multiple Facets (AND Logic Between Facets)

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
        "facetKey": "technicalSuitability",
        "operator": "OR",
        "keys": ["unreasonable"]
      }
    ]
  }
}
```

Facets are combined with AND logic - fact sheets must match ALL facet filters.

### NOR Operator (Exclusion)

```json
{
  "facetKey": "functionalSuitability",
  "operator": "NOR",
  "keys": ["perfect", "appropriate"]
}
```

Excludes fact sheets with functional fit of "perfect" or "appropriate".

### Date Filter

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

### Tag Filter

```json
{
  "facetKey": "_TAGS_",
  "operator": "OR",
  "keys": ["tag-id-1", "tag-id-2"]
}
```

## Sorting

Along with filters, you can sort results:

```json
{
  "sortings": [
    {
      "key": "displayName",
      "order": "asc"
    }
  ]
}
```

**Available sort keys:**
- `displayName`: Alphabetical by name
- `updatedAt`: Last modified date
- `createdAt`: Creation date
- `completion`: Completion percentage

**Sort orders:**
- `asc`: Ascending (A-Z, oldest first, lowest completion first)
- `desc`: Descending (Z-A, newest first, highest completion first)

## Full Query Example

```graphql
query ($filter: FilterInput!, $sortings: [Sorting]) {
  allFactSheets(filter: $filter, sort: $sortings, first: 100) {
    totalCount
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
        "keys": ["_noDescription_"]
      }
    ]
  },
  "sortings": [
    {
      "key": "completion",
      "order": "asc"
    }
  ]
}
```

This finds all Providers missing descriptions, sorted by completion percentage (lowest first).
