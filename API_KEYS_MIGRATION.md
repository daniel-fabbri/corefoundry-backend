# API Keys Migration Guide

## How to Run the Migration

### Option 1: Using psql (Recommended)

```bash
# Navigate to backend directory
cd corefoundry-backend

# Run migration
psql -U corefoundry_user -d corefoundry_db -f migrate_api_keys.sql

# Or with password prompt
PGPASSWORD=your_password psql -U corefoundry_user -d corefoundry_db -f migrate_api_keys.sql
```

### Option 2: Using Python script

```python
# Create a file: run_api_keys_migration.py
from corefoundry.app.db.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    with open('migrate_api_keys.sql', 'r') as f:
        sql = f.read()
    conn.execute(text(sql))
    conn.commit()
    print("✅ Migration completed successfully")
```

Then run:
```bash
python run_api_keys_migration.py
```

### Option 3: Using init_db.sh

Add to your `init_db.sh`:
```bash
psql -U corefoundry_user -d corefoundry_db -f migrate_api_keys.sql
```

## What This Migration Does

1. Creates `api_keys` table with:
   - Secure key hash storage (never stores plaintext)
   - User association (FK to auth_users)
   - Key metadata (name, prefix, usage tracking)
   - Expiration and activation controls

2. Creates indexes for performance:
   - `user_id` for fast user key lookup
   - `key_hash` for fast authentication
   - `is_active` for filtering active keys

3. Sets up proper permissions for the database user

## Testing the Migration

After running, verify:

```sql
-- Check table exists
\dt api_keys

-- Check structure
\d api_keys

-- Verify empty (should return 0)
SELECT COUNT(*) FROM api_keys;
```

## API Key Format

Generated keys look like: `cfk_random_secure_string_here`

- Prefix: `cfk_` (CoreFoundry Key)
- Token: 32-byte secure random string
- Total length: ~47 characters

## Usage in API Requests

```bash
curl -H "X-API-Key: cfk_your_key_here" \
     http://localhost:8000/api/agents
```
