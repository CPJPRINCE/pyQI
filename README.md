# pyQi

[![Supported Versions](https://img.shields.io/pypi/pyversions/pyqi.svg)](https://pypi.org/project/pyqi)

A Python client library for interacting with Qi's Content and Collections Management Software API. Provides both synchronous and asynchronous interfaces for querying, creating, updating, and deleting records with full bulk operation support.

## Table of Contents

- [Quick Start](#quick-start)
- [Version & Package Info](#version--package-info)
- [Why Use This Library?](#why-use-this-library)
- [Key Features](#key-features)
- [Authentication](#authentication)
  - [Credentials File](#credentials-file)
  - [Username + Keyring](#username--keyring)
- [Sync vs Async](#sync-vs-async)
- [API Operations](#api-operations)
  - [Search & Retrieval](#search--retrieval)
  - [Data Import](#data-import)
  - [Data Update](#data-update)
  - [Data Deletion](#data-deletion)
  - [Bulk Operations](#bulk-operations)
- [XML Metadata](#xml-metadata)
- [Output Formats](#output-formats)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Developers](#developers)
- [Contributing](#contributing)

## Quick Start

### 1) Install

```bash
pip install -U pyqi_api
```

Or install from source:

```bash
git clone https://github.com/CPJPRINCE/pyqi.git
cd pyqi
pip install -e .
```
### 2) Sync Usage

```python
from pyQi.pyQi_api import QiAPI

api = QiAPI(
    username='your.username@example.com',
    server='yourtenant.qi.com',
    password='your_password'
)

# Search for records
records = api.get_request(
    table='YourTable',
    fields_to_search='name',
    search_term='John Doe'
)
```

### 3) Async Usage

```python
from pyQi.pyQi_api_async import QiAPIAsync

api = QiAPIAsync(
    username='your.username@example.com',
    server='yourtenant.qi.com',
    password='your_password'  # or None to prompt
)

# Search for records
records = await api.get_request(
    table='YourTable',
    fields_to_search='name',
    search_term='John Doe'
)

# Export to Excel
await api.search_to_excel(
    output_file='results.xlsx',
    table='YourTable',
    fields_to_search='status',
    search_term='active'
)

await api.close_session()
```

## Version & Package Info

**Python Version**

- Python 3.9+ required

**Core dependencies**

- `aiohttp` (async HTTP client)
- `requests` (sync HTTP client)
- `pandas` (data processing)
- `keyring` (secure credential storage)
- `pypreservica` (required import)

## Why Use This Library?

This library provides a Pythonic interface to Qi's API, simplifying:

- **Multi-record queries** with field/term pairs
- **Bulk operations** (import, update, delete from files)
- **Format flexibility** (Excel, CSV, JSON, XML input/output)
- **Async concurrency** with rate limiting for high-throughput workflows
- **Credential security** via integrated keyring support
- **Relationship resolution** for linked table lookups

Typical use cases:

- Bulk search and export workflows
- Migrating data from external sources
- Updating many records consistently
- Automated reporting and data extraction

## Key Features

- **Dual API**: Async and synchronous implementations
- **Search operations** with multiple field/search term combinations
- **Bulk import/update/delete** from spreadsheets and JSON
- **Multi-format support**: Excel, CSV, JSON, XML input; Excel, CSV, JSON, XML, DataFrame, dict output
- **Automatic relationship lookups** for linked field resolution
- **List field validation** against configured list values
- **Rate limiting** via configurable semaphore (default 10 concurrent)
- **Secure credential storage** with optional keyring integration
- **Field-level metadata** retrieval and caching

## Authentication

### Credentials File

Create a `credentials.properties` file:

```properties
username=your.username@example.com
password=your-password
server=yourtenant.qi.com
```

Pass to constructor:

```python
api = QiAPIAsync(
    credentials_file='/path/to/credentials.properties'
)
```

### Username + Keyring

```python
api = QiAPIAsync(
    username='your.username@example.com',
    server='yourtenant.qi.com',
    password=None,  # Will prompt
    use_keyring=True,
    save_password_to_keyring=True
)

# After login, password is cached in system keyring
```

Retrieve stored password on next run:

```python
# Keyring will attempt retrieval automatically
api = QiAPIAsync(
    username='your.username@example.com',
    server='yourtenant.qi.com',
    use_keyring=True
)
```

## Sync vs Async

### Async (Recommended for bulk operations)

```python
import asyncio
from pyQi.pyQi_api_async import QiAPIAsync

async def main():
    api = QiAPIAsync('user', 'server', 'password')
    
    # Multiple operations can run concurrently
    results = await api.get_request(table='Table1', fields_to_search='id', search_term='123')
    
    await api.close_session()

asyncio.run(main())
```

**Benefits:**
- Concurrent requests with rate limiting
- Better performance for bulk operations
- Non-blocking I/O

**Warning:**
- Ensure your system is capable of supporting concurrent requests, otherwise may cause system crashes.
- If causing issues lower the number of concurrencies see [here](#rate-limiting)

### Sync (Simpler, blocking)

```python
from pyQi.pyQi_api import QiAPI

api = QiAPI('user', 'server', 'password')

results = api.get_request(table='Table1', fields_to_search='id', search_term='123')
```

**Benefits:**
- Simpler error handling
- Easier to debug
- Suitable for simple scripts / small uploads

## API Operations

### Search & Retrieval

Basic search:

```python
# Single field search
results = await api.get_request(
    table='Contacts',
    fields_to_search='email',
    search_term='john@example.com'
)

# Multiple field search (paired)
results = await api.get_request(
    table='Contacts',
    fields_to_search=['first_name', 'last_name'],
    search_term=['John', 'Doe']
)

# Search entire table
results = await api.get_request(table='Contacts')
```

**Supported kwargs:**

All optional elements of the QI API are supported as a kwarg.

- `offset`: result offset (default 0)
- `per_page`: results per page (default unlimited)
- `sort_by`: field name to sort by
- `sort_direction`: 'asc' or 'desc'
- `fields`: comma-separated field names to return
- `since`: last modification timestamp filter

Find single record:

```python
record = await api.find_record_by_id(table='Contacts', id='12345')
```

### Data Import

Import from file:

```python
await api.import_from_file(
    file='/path/to/data.xlsx',
    table='Contacts',
    auto_approve=False
)
```

Supports:

- `.xlsx`, `.xls`, `.xlsm` (Excel)
- `.csv`, `.txt`, `.tsv` (Delimited)
- `.xml`, `.ods` (XML/ODS)
- `.json`

**Special columns:**

- `relationship:TableName` - Automatic relationship field resolution
- `list:FieldName` - List value validation against Qi configuration

### Data Update

Update from file with lookup:

```python
await api.update_from_file(
    file='/path/to/updates.xlsx',
    table='Contacts',
    lookup_field='email',  # if no 'id' column
    auto_approve=False
)
```

Update records matching search criteria:

```python
await api.update_from_search(
    table='Contacts',
    fields_to_search='status',
    search_term='inactive',
    fields_to_update={'status': 'archived', 'modified_by': 'script'},
    auto_approve=False
)
```

### Data Deletion

Delete from file:

```python
await api.delete_from_file(
    file='/path/to/ids_to_delete.xlsx',
    table='Contacts',
    lookup_field='email',  # if no 'id' column
    auto_approve=False
)
```

Delete records matching search **(Use with caution!)**:

```python
await api.delete_from_search(
    table='Contacts',
    fields_to_search='status',
    search_term='inactive',
    auto_approve=False
)
```

## Relationships / List Lookups

Library includes helpers for looking up Relationship and List IDs, allowing for inputs to be configured without knowing the specific ID.

- **Relationship lookup**: Resolve related table IDs for linked records
- **List field resolution**: Map human-readable list values to Qi list IDs

Example workflow:

```python
await api.lookup_table_id('RelatedTable')
await api.lookup_lists(table='Contacts')

# Now import handles relationship:* and list:* columns automatically
await api.import_from_file('data.xlsx', table='Contacts')
```

## Output Formats

Search results can be exported to multiple formats:

```python
# Excel
await api.search_to_excel(
    output_file='results.xlsx',
    table='Contacts',
    fields_to_search='status',
    search_term='active'
)

# CSV
await api.search_to_csv('results.csv', table='Contacts', ...)

# JSON (JSONL)
await api.search_to_json_df('results.jsonl', table='Contacts', ...)

# JSON (raw list)
await api.search_to_json('results.json', table='Contacts', ...)

# XML
await api.search_to_xml('results.xml', table='Contacts', ...)

# Pandas DataFrame
df = await api.search_to_df(table='Contacts', ...)

# Python dict list
records = await api.search_to_dict(table='Contacts', ...)
```

## Rate Limiting

The async API uses `asyncio.Semaphore` to limit concurrent requests:

```python
# Default: 10 concurrent requests
api = QiAPIAsync(...)

# Change limit
api.create_sem(limit=5)  # More restrictive
api.create_sem(limit=50)  # More permissive
```

All HTTP operations respect the semaphore limit:

- `get_request()`, `put_request()`, `post_request()`, `delete_request()`
- `get_types()`, `get_list()` (utility methods)

## Logging

Set a log file and logging levels:

```python
api = QiAPIAsync(..., log_file = "/path/to/logfile.log", log_level={INFO,DEBUG,ERROR})
```

## Examples

### Bulk Update with Search-Replace

```python
import asyncio
from pyQi.pyQi_api_async import QiAPIAsync

async def bulk_update():
    api = QiAPIAsync('user', 'server', 'password')
    
    # Find all records with old status
    results = await api.get_request(
        table='Tasks',
        fields_to_search='status',
        search_term='deprecated'
    )
    
    # Update to new status
    await api.update_from_search(
        table='Tasks',
        fields_to_search='status',
        search_term='deprecated',
        fields_to_update={'status': 'archived', 'archived_date': '2024-03-06'},
        auto_approve=True
    )
    
    await api.close_session()

asyncio.run(bulk_update())
```

### Export Search Results

```python
async def export_report():
    api = QiAPIAsync('user', 'server', 'password')
    
    await api.search_to_excel(
        output_file='active_contacts.xlsx',
        table='Contacts',
        fields_to_search='status',
        search_term='active',
        sort_by='last_name',
        sort_direction='asc'
    )
    
    await api.close_session()

asyncio.run(export_report())
```

### Import with Relationship Resolution

```python
async def import_with_relationships():
    api = QiAPIAsync('user', 'server', 'password')
    
    # Spreadsheet columns: name, email, company:Companies
    # The company column will auto-resolve to company ID
    await api.import_from_file(
        file='import.xlsx',
        table='Contacts',
        auto_approve=False
    )
    
    await api.close_session()

asyncio.run(import_with_relationships())
```

## Troubleshooting

**Import errors**

- Ensure package installed: `pip install -e .`
- Check Python version: 3.9+
- Verify all dependencies: `pip install aiohttp requests pandas keyring`

**Authentication failures**

- Verify server format (no `https://` prefix)
- Check username spelling and tenant name
- Confirm password is correct
- Keyring may have stale credentials: manually clear or reinstall

**Rate limiting / timeouts**

- Reduce semaphore limit: `api.create_sem(limit=5)`
- Check network connectivity to Qi server
- Verify server isn't blocking concurrent connections

**No results in search**

- Confirm table name spelling
- Verify field name matches Qi schema
- Check if search term is correctly formatted for field type

**Relationship columns not resolving**

- Use format: `relationship:TableName` in header
- Ensure related table exists in Qi
- Verify field has relationship configured in Qi

## Developers

### Local install

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\Activate.ps1  # Windows

pip install -e .
```

### Run tests

```bash
pytest
```

### Project structure

```
pyQi/
├── __init__.py
├── common.py                # Shared auth, utilities
├── pyQi_api.py              # Sync API implementation
├── pyQi_api_async.py        # Async API implementation
├── json_builder.py          # JSON parsing utilities
├── tests                    # Tests folder
└── samples                  # Example data
```

## Contributing

Issues and pull requests are welcome.

Please include:

- Python version and OS
- Minimal reproducible example
- Expected vs actual behavior
- Traceback/error messages
- Qi server version (if applicable)

Licensed under Apache License 2.0.