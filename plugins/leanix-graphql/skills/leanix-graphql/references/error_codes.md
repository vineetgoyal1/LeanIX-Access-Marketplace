# LeanIX GraphQL Error Codes and Solutions

## Common Error Messages

### Authentication Errors

**"Unauthorized" or "Invalid token"**
- **Cause:** Access token expired or invalid
- **Solution:** Obtain new access token via OAuth2 endpoint
- **Prevention:** Implement token refresh logic

### Query/Mutation Errors

**"Validation error of type FieldUndefined: Field X is undefined"**
- **Cause:** Requested field doesn't exist in schema
- **Solution:** Check schema in GraphiQL Documentation Explorer
- **Example:** Typo in field name (`descriptio` instead of `description`)

**"The path '/fieldName' is invalid in FactSheet schema Application"**
- **Cause:** Invalid path in JSON Patch operation
- **Solution:** Verify path format and field name
- **Common mistake:** Wrong path syntax or non-existent field

**"Error in Request. Transaction is rolled back!"**
- **Cause:** One or more mutations in a batch failed
- **Impact:** ALL mutations in the batch are rolled back (none applied)
- **Solution:** Check individual mutation errors, validate data, retry individually

### Pagination Errors

**"Cursor is invalid or expired"**
- **Cause:** Cursor from old request no longer valid
- **Solution:** Restart pagination from beginning
- **Note:** Data changes between requests can invalidate cursors

### Relation Errors

**"Invalid relation type"**
- **Cause:** Relation type doesn't exist or isn't valid for fact sheet type
- **Solution:** Check available relations for fact sheet type in schema

**"Malformed relation value"**
- **Cause:** Relation value not properly formatted as JSON string
- **Solution:** Ensure value is JSON string with escaped quotes
- **Example:** Use `"{\"factSheetId\":\"id\"}"` not `{"factSheetId":"id"}`

## Error Response Structure

```json
{
  "data": null,
  "errors": [
    {
      "message": "Error description",
      "locations": [
        {
          "line": 6,
          "column": 9
        }
      ],
      "path": ["mutationAlias"],
      "extensions": {
        "errorType": "BUSINESS_LOGIC"
      }
    }
  ]
}
```

**Fields:**
- `message`: Human-readable error description
- `locations`: Line/column in query where error occurred
- `path`: Which operation failed (useful in batch mutations)
- `extensions.errorType`: Error category (BUSINESS_LOGIC, VALIDATION, etc.)

## Handling Strategies

### Batch Mutation Failures

```python
def create_with_fallback(items):
    """Try batch create, fallback to individual on failure"""
    try:
        return create_batch(items)
    except GraphQLError as e:
        if "Transaction is rolled back" in str(e):
            # Batch failed, try one by one
            results = []
            for item in items:
                try:
                    results.append(create_single(item))
                except GraphQLError as item_error:
                    print(f"Failed to create {item}: {item_error}")
            return results
        raise
```

### Token Refresh

```python
class LeanIXClient:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None

    def get_token(self):
        if not self.access_token or time.time() > self.token_expiry:
            # Refresh token
            response = requests.post(...)
            self.access_token = response.json()['access_token']
            self.token_expiry = time.time() + 3600  # 1 hour
        return self.access_token
```

### Retry Logic

```python
def execute_with_retry(query, variables, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = execute_graphql(query, variables)
            if "errors" not in result:
                return result

            # Check if retryable error
            errors = result["errors"]
            if any("token" in e["message"].lower() for e in errors):
                # Token error - refresh and retry
                refresh_token()
                continue

            # Non-retryable error
            raise GraphQLError(errors)

        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```
