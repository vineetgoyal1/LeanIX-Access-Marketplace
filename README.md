# LeanIX Access Marketplace

Enterprise architecture management tools and skills for working with the LeanIX API (GraphQL and REST).

## Plugins

### leanix-graphql

Use LeanIX GraphQL API for querying and managing enterprise architecture data.

**Features:**
- Query fact sheets with filtering and pagination
- Create/update fact sheets using JSON Patch operations
- Batch operations (up to 50 fact sheets per request)
- Manage relations between fact sheets
- Complex facet-based filtering
- Data quality analysis

**Use Cases:**
- Get providers/applications from LeanIX
- Create or update fact sheets (Applications, Providers, ITComponents, etc.)
- Search with filters (data quality, types, tags, lifecycle, etc.)
- Find data quality issues
- Perform batch operations
- Write Python scripts that interact with LeanIX

### leanix-rest (coming soon)

REST API access for LeanIX operations.

## Installation

```bash
/plugin install leanix-graphql@LeanIX-Access-Marketplace
```

## Author

Vineet Goyal (vineet.goyal@sap.com)
