# LeanIX GraphQL Plugin

Use LeanIX GraphQL API for querying and managing enterprise architecture data.

## Overview

This plugin provides comprehensive support for working with the SAP LeanIX GraphQL API. It enables you to query, create, update, and manage enterprise architecture fact sheets (Applications, Providers, ITComponents, etc.) and their relationships.

## When to Use

Use this skill when you need to:
- Query providers or applications from LeanIX
- Create or update fact sheets programmatically
- Filter by data quality, completion scores, tags, etc.
- Perform batch operations (up to 50 fact sheets per request)
- Manage relations between fact sheets
- Write Python scripts that interact with LeanIX
- Analyze data quality issues

## Key Features

- **Query Operations** - Get fact sheets with filtering, pagination, and specific field selection
- **Mutations** - Create/update fact sheets using JSON Patch operations
- **Batch Operations** - Create multiple fact sheets in one request
- **Relations Management** - Create/update/delete relations between fact sheets
- **Filtering** - Complex facet-based filtering (data quality, types, tags, lifecycle, etc.)
- **Error Handling** - Comprehensive error handling patterns

## Critical Warnings

⚠️ **GraphQL Always Returns HTTP 200**: Even on errors. Must check `errors` field in response body.

⚠️ **Batch Mutation Rollback**: If ONE mutation in a batch fails, ALL mutations fail (transaction rollback).

⚠️ **Lifecycle Updates Are All-or-Nothing**: When updating lifecycle, you MUST include ALL phases or they will be deleted.

## Documentation

The skill includes comprehensive documentation:
- Main SKILL.md - Complete guide with examples
- references/advanced_examples.md - External IDs, aliases, lifecycle, quality seal, etc.
- references/facets_reference.md - All available facet keys by fact sheet type
- references/error_codes.md - Common error messages and solutions
- scripts/leanix_client.py - Reusable Python client module

## Version

1.0.0

## Author

Vineet Goyal (vineet.goyal@sap.com)
