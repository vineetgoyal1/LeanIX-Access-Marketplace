"""
Reusable LeanIX GraphQL client module.

Usage:
    from leanix_client import LeanIXClient

    client = LeanIXClient(
        subdomain=os.getenv('LEANIX_SUBDOMAIN'),
        api_token=os.getenv('LEANIX_API_TOKEN')
    )

    # Query
    providers = client.query_all_providers()

    # Create
    provider = client.create_provider("Provider Name", "Description")

    # Update
    client.update_fact_sheet(provider_id, [
        {"op": "replace", "path": "/description", "value": "New description"}
    ])
"""

import os
import time
import json
import requests
from typing import Dict, List, Optional, Any


class GraphQLError(Exception):
    """GraphQL-specific error"""
    def __init__(self, errors: List[Dict]):
        self.errors = errors
        messages = [e.get('message', 'Unknown error') for e in errors]
        super().__init__(f"GraphQL errors: {'; '.join(messages)}")


class LeanIXClient:
    """LeanIX GraphQL API client with authentication and error handling"""

    def __init__(self, subdomain: str, api_token: str):
        if not subdomain or not api_token:
            raise ValueError("subdomain and api_token are required")

        self.subdomain = subdomain
        self.api_token = api_token
        self.graphql_url = f'https://{subdomain}.leanix.net/services/pathfinder/v1/graphql'
        self.oauth2_url = f'https://{subdomain}.leanix.net/services/mtm/v1/oauth2/token'

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None

    def _obtain_access_token(self) -> str:
        """Get or refresh OAuth2 access token"""
        # Check if token is still valid
        if self._access_token and self._token_expiry and time.time() < self._token_expiry:
            return self._access_token

        # Obtain new token
        response = requests.post(
            self.oauth2_url,
            auth=("apitoken", self.api_token),
            data={"grant_type": "client_credentials"}
        )
        response.raise_for_status()

        result = response.json()
        self._access_token = result['access_token']
        # Set expiry to 50 minutes (tokens typically valid for 1 hour)
        self._token_expiry = time.time() + 3000

        return self._access_token

    def execute(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query or mutation.

        Args:
            query: GraphQL query or mutation string
            variables: Optional variables dict

        Returns:
            Response data dict

        Raises:
            GraphQLError: If GraphQL errors are present in response
            requests.RequestException: If HTTP request fails
        """
        access_token = self._obtain_access_token()

        data = {'query': query}
        if variables:
            data['variables'] = variables

        response = requests.post(
            url=self.graphql_url,
            headers={'Authorization': f'Bearer {access_token}'},
            data=json.dumps(data)
        )
        response.raise_for_status()

        result = response.json()

        # Check for GraphQL errors
        if "errors" in result:
            raise GraphQLError(result["errors"])

        return result.get("data", {})

    def query_fact_sheet(self, fact_sheet_id: str, fields: Optional[List[str]] = None) -> Dict:
        """
        Query a single fact sheet by ID.

        Args:
            fact_sheet_id: Fact sheet UUID
            fields: Optional list of fields to return (default: id, name, type, description)

        Returns:
            Fact sheet data dict
        """
        if fields is None:
            fields = ["id", "name", "type", "description", "completion { percentage }"]

        fields_str = "\n".join(fields)

        query = f"""
            query ($id: ID!) {{
                factSheet(id: $id) {{
                    {fields_str}
                }}
            }}
        """

        data = self.execute(query, {"id": fact_sheet_id})
        return data["factSheet"]

    def query_all_fact_sheets(
        self,
        fact_sheet_type: str,
        filters: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        page_size: int = 100
    ) -> List[Dict]:
        """
        Query all fact sheets with pagination.

        Args:
            fact_sheet_type: Type (Application, Provider, ITComponent, etc.)
            filters: Optional filter dict with facetFilters
            fields: Optional list of fields to return
            page_size: Results per page (default: 100)

        Returns:
            List of fact sheet dicts
        """
        if fields is None:
            fields = ["id", "displayName", "completion { percentage }"]

        fields_str = "\n".join(fields)

        query = """
            query ($filter: FilterInput!, $first: Int!, $cursor: String) {
                allFactSheets(
                    filter: $filter,
                    first: $first,
                    after: $cursor
                ) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        node {
                            """ + fields_str + """
                        }
                    }
                }
            }
        """

        # Build filter
        if filters is None:
            filters = {}

        # Ensure FactSheetTypes filter exists
        facet_filters = filters.get("facetFilters", [])
        has_type_filter = any(f.get("facetKey") == "FactSheetTypes" for f in facet_filters)

        if not has_type_filter:
            facet_filters.insert(0, {
                "facetKey": "FactSheetTypes",
                "operator": "OR",
                "keys": [fact_sheet_type]
            })
            filters["facetFilters"] = facet_filters

        # Paginate
        all_results = []
        cursor = None

        while True:
            variables = {"filter": filters, "first": page_size}
            if cursor:
                variables["cursor"] = cursor

            data = self.execute(query, variables)
            fact_sheets = data["allFactSheets"]

            all_results.extend([edge["node"] for edge in fact_sheets["edges"]])

            if not fact_sheets["pageInfo"]["hasNextPage"]:
                break

            cursor = fact_sheets["pageInfo"]["endCursor"]

        return all_results

    def create_fact_sheet(
        self,
        name: str,
        fact_sheet_type: str,
        patches: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create a fact sheet.

        Args:
            name: Fact sheet name
            fact_sheet_type: Type (Application, Provider, ITComponent, etc.)
            patches: Optional JSON patch operations for additional fields

        Returns:
            Created fact sheet data dict
        """
        mutation = """
            mutation ($input: BaseFactSheetInput!, $patches: [Patch]) {
                createFactSheet(input: $input, patches: $patches) {
                    factSheet {
                        id
                        name
                        type
                    }
                }
            }
        """

        variables = {
            "input": {
                "name": name,
                "type": fact_sheet_type
            }
        }

        if patches:
            variables["patches"] = patches

        data = self.execute(mutation, variables)
        return data["createFactSheet"]["factSheet"]

    def update_fact_sheet(
        self,
        fact_sheet_id: str,
        patches: List[Dict],
        comment: Optional[str] = None
    ) -> Dict:
        """
        Update a fact sheet.

        Args:
            fact_sheet_id: Fact sheet UUID
            patches: List of JSON patch operations
            comment: Optional comment for the update

        Returns:
            Updated fact sheet data dict
        """
        mutation = """
            mutation ($id: ID!, $patches: [Patch]!, $comment: String) {
                updateFactSheet(id: $id, patches: $patches, comment: $comment) {
                    factSheet {
                        id
                        name
                    }
                }
            }
        """

        variables = {
            "id": fact_sheet_id,
            "patches": patches
        }

        if comment:
            variables["comment"] = comment

        data = self.execute(mutation, variables)
        return data["updateFactSheet"]["factSheet"]

    def archive_fact_sheet(self, fact_sheet_id: str, comment: str) -> Dict:
        """
        Archive (soft delete) a fact sheet.

        Args:
            fact_sheet_id: Fact sheet UUID
            comment: Reason for archiving

        Returns:
            Archived fact sheet data dict
        """
        return self.update_fact_sheet(
            fact_sheet_id,
            patches=[{"op": "add", "path": "/status", "value": "ARCHIVED"}],
            comment=comment
        )

    # Convenience methods for common operations

    def create_provider(self, name: str, description: str) -> Dict:
        """Create a Provider fact sheet"""
        return self.create_fact_sheet(
            name=name,
            fact_sheet_type="Provider",
            patches=[
                {"op": "add", "path": "/description", "value": description}
            ]
        )

    def query_all_providers(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Query all Provider fact sheets"""
        return self.query_all_fact_sheets("Provider", filters)

    def query_incomplete_providers(self) -> List[Dict]:
        """Query providers with data quality issues"""
        filters = {
            "facetFilters": [
                {
                    "facetKey": "DataQuality",
                    "operator": "OR",
                    "keys": ["_noDescription_", "_noResponsible_"]
                }
            ]
        }
        return self.query_all_providers(filters)


# Example usage
if __name__ == "__main__":
    # Initialize client from environment variables
    client = LeanIXClient(
        subdomain=os.getenv('LEANIX_SUBDOMAIN'),
        api_token=os.getenv('LEANIX_API_TOKEN')
    )

    # Query all providers
    providers = client.query_all_providers()
    print(f"Found {len(providers)} providers")

    # Query incomplete providers
    incomplete = client.query_incomplete_providers()
    print(f"Found {len(incomplete)} incomplete providers")

    # Create a provider
    provider = client.create_provider("Test Provider", "A test provider")
    print(f"Created provider: {provider['id']}")

    # Update provider
    client.update_fact_sheet(
        provider['id'],
        patches=[
            {"op": "replace", "path": "/description", "value": "Updated description"}
        ]
    )
    print("Updated provider description")
