# Advanced Monitoring & Analysis Guide

## Overview

The chatbot now provides **deep analysis of database metrics**, not just raw values. Every monitoring query includes:
- 🔍 **Root Cause Analysis** - Why is this happening?
- 💡 **Remediation Recommendations** - What to do about it?
- 📊 **Business Impact** - How much performance is lost?
- ✅ **Actionable Steps** - Exact commands to run

---

## New Monitoring Tools

### 1. Analyze Slow Queries (Deep Diagnosis)

**Purpose**: Identify slow queries with ROOT CAUSE and REMEDIATION

**When to use**: 
- "Database is slow"
- "Performance degradation"
- "High query times"

**What it returns**:
- Severity level (CRITICAL/HIGH/MEDIUM/LOW)
- Exact metrics (execution time, call count, impact)
- Root cause analysis from query patterns
- Specific remediation recommendations
- Business impact in seconds/minutes/hours wasted

**Example Response**:
```
SLOW QUERY ANALYSIS
═══════════════════

Query: SELECT * FROM customers WHERE name LIKE '%John%'
Severity: HIGH (523ms average execution time)
Executions: 150 calls
Total Impact: ~78 seconds wasted per cycle

ROOT CAUSES:
  ├─ SELECT * → Fetching unnecessary columns
  ├─ LIKE pattern → Full text scan, not indexed
  └─ No WHERE filtering on indexed columns

REMEDIATION:
  1. Create index: CREATE INDEX idx_customers_name ON customers(name)
  2. Modify query: SELECT id, name, email FROM customers WHERE name = 'John'
  3. Run ANALYZE: ANALYZE customers;

EXPECTED IMPROVEMENT: 80% reduction (from 523ms to ~100ms)
```

**Usage**:
```
User: "Why are queries slow?"
Bot calls: analyze_slow_queries(threshold_ms=100, limit=5)
Bot returns: Detailed analysis with recommendations
```

---

### 2. Check Missing Indexes

**Purpose**: Identify indexing opportunities that could improve performance

**When to use**:
- "Optimize database"
- "Improve query speed"
- "Which tables need indexing?"

**What it returns**:
- Tables with high sequential scan counts
- Recommended index columns
- Suggested CREATE INDEX statements
- Estimated performance improvement (50-80%)

**Example Response**:
```
MISSING INDEX ANALYSIS
══════════════════════

Table: public.customers
  Sequential Scans: 1,250
  Index Scans: 15
  Scan Ratio: 83.3 (mostly sequential)
  
  Recommended Index:
  CREATE INDEX idx_customers_email_name ON customers (email, name);
  
  Potential Columns: email, name, created_at
  Expected Improvement: 70% query performance improvement

Table: public.orders
  Sequential Scans: 450
  Index Scans: 200
  Scan Ratio: 2.25
  
  Recommended Index:
  CREATE INDEX idx_orders_customer_date ON orders (customer_id, created_at);
  
  Potential Columns: customer_id, created_at, product_id
  Expected Improvement: 60% query performance improvement
```

**Usage**:
```
User: "What indexes are we missing?"
Bot calls: check_missing_indexes()
Bot returns: Analysis with specific CREATE INDEX statements
```

---

### 3. Check Table Bloat

**Purpose**: Identify tables needing maintenance (VACUUM/ANALYZE)

**When to use**:
- "Database maintenance"
- "Space issues"
- "Performance degradation over time"

**What it returns**:
- Table bloat percentage (dead tuples)
- Size and row counts
- Last maintenance times
- VACUUM/ANALYZE recommendations
- Exact remediation commands

**Example Response**:
```
TABLE BLOAT ANALYSIS
════════════════════

Table: public.customers
  Size: 2.5 MB
  Dead Tuples: 5,420 (22.5% of total)
  Status: URGENT - Run VACUUM ANALYZE
  Last Maintenance: 3 days ago
  
  Action: VACUUM ANALYZE customers;
  Expected Result: Reclaim ~560 KB of space

Table: public.orders
  Size: 15 MB
  Dead Tuples: 1,230 (8.2% of total)
  Status: MEDIUM - Consider VACUUM
  Last Maintenance: 18 hours ago
  
  Action: VACUUM ANALYZE orders;
  Expected Result: Reclaim ~1.2 MB of space
```

**Usage**:
```
User: "Is the database bloated?"
Bot calls: check_table_bloat()
Bot returns: Maintenance recommendations with commands
```

---

### 4. Get Performance Schema

**Purpose**: Access PostgreSQL system catalogs for advanced diagnostics

**Query Types**:

#### overview
```sql
SELECT datname, heap_blks_hit, heap_blks_read, idx_blks_hit, idx_blks_read
FROM pg_statio_user_tables
```
Shows I/O statistics and cache efficiency

#### index_effectiveness
```sql
SELECT indexname, idx_scan, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
```
Identifies unused and ineffective indexes

#### connection_stats
```sql
SELECT datname, count(*) as active_connections
FROM pg_stat_activity
GROUP BY datname
```
Shows active connections and query times

#### cache_efficiency
```sql
SELECT
  sum(heap_blks_hit) as cache_hits,
  sum(heap_blks_read) as disk_reads,
  ROUND(100 * sum(heap_blks_hit) / ...) as hit_ratio
FROM pg_statio_user_tables
```
Shows cache hit ratio and I/O efficiency

**Usage**:
```
User: "Show me index effectiveness"
Bot calls: get_performance_schema(query_type='index_effectiveness')
Bot returns: Detailed index statistics
```

---

### 5. Execute Remediation

**Purpose**: Run maintenance and optimization commands with safety controls

**Supported Actions**:
- `VACUUM` - Remove dead tuples
- `ANALYZE` - Update statistics
- `VACUUM_ANALYZE` - Combined operation
- `REINDEX` - Rebuild indexes

**Safety Features**:
- Requires `allow_remediation` in guardrails
- Only runs authorized commands
- Prevents accidental data loss
- Logs all operations

**Example**:
```
User: "Run VACUUM on customers table"
Bot calls: execute_remediation(action='VACUUM', table='customers')
Bot returns: Success/Error with operation details
```

**Usage**:
```python
# Configuration to enable remediation
guardrails = {
    "allow_remediation": True,  # Must be enabled
    "allow_writes": False,
    "allow_ddl": False
}
```

---

## Analysis Workflow

### Step 1: Diagnose the Problem
```
User: "Database performance is degrading"
↓
Bot runs: analyze_slow_queries()
↓
Returns: Top slow queries with root causes
```

### Step 2: Find Root Causes
```
From analysis, bot identifies:
- Sequential scans (missing indexes)
- Table bloat (needs VACUUM)
- Query inefficiency (needs rewrite)
↓
Bot runs: check_missing_indexes() + check_table_bloat()
↓
Returns: Specific recommendations
```

### Step 3: Execute Fixes
```
Based on findings, bot recommends:
1. CREATE INDEX idx_... ON table (columns)
2. VACUUM ANALYZE table
3. Rewrite query to use index
↓
Bot calls: execute_remediation(action='VACUUM_ANALYZE', table=...)
↓
Returns: Success confirmation
```

### Step 4: Verify Improvements
```
After fixes, bot verifies:
- get_metrics() → Check connections, cache ratio
- analyze_slow_queries() → Compare new timings
- get_performance_schema() → Verify index usage
↓
Shows: Performance improvement % before/after
```

---

## Response Format

### ✅ Good Response (Analysis + Interpretation)

```
DATABASE PERFORMANCE ANALYSIS
══════════════════════════════

ISSUE DETECTED: High Query Latency
Severity: HIGH
Root Cause: Missing indexes on frequently accessed columns

AFFECTED QUERIES:
  • SELECT * FROM customers WHERE email = ?  (523ms avg, 150 calls/cycle)
  • SELECT * FROM orders WHERE customer_id = ?  (347ms avg, 230 calls/cycle)

BUSINESS IMPACT:
  • 78 seconds wasted per monitoring cycle
  • 463 seconds (7.7 minutes) per hour
  • ~184 hours per month in wasted query time

REMEDIATION STEPS:
  1. Create indexes:
     CREATE INDEX idx_customers_email ON customers(email);
     CREATE INDEX idx_orders_customer ON orders(customer_id);
  
  2. Update table statistics:
     ANALYZE customers;
     ANALYZE orders;
  
  3. Verify improvement:
     SELECT * FROM pg_stat_user_indexes WHERE indexname LIKE 'idx_%';

EXPECTED RESULTS:
  • Query latency: 523ms → 100ms (80% improvement)
  • Cycles to completion: 47 hours → 9 hours per month
  • Database responsiveness: Significantly improved
```

### ❌ Bad Response (Raw Data)

```
{"slowQueries": [
  {"query": "SELECT * FROM customers WHERE email = ?", "mean_time": 523.45, "calls": 150},
  {"query": "SELECT * FROM orders WHERE customer_id = ?", "mean_time": 347.2, "calls": 230}
]}
```

---

## Common Scenarios

### Scenario 1: "Database is slow"

```
User: "The database is slow. What's wrong?"

Bot Flow:
1. analyze_slow_queries() → Get slow queries + diagnosis
2. check_missing_indexes() → Find index opportunities
3. check_table_bloat() → Check maintenance needs
4. get_performance_schema(query_type='cache_efficiency') → Check cache ratio

Bot Response:
"I've identified 3 slow queries consuming 120 seconds per cycle:
- Missing indexes on 2 tables (CREATE INDEX statements provided)
- Table bloat on customers table (22% dead tuples)
- Cache hit ratio is only 65% (should be >90%)

Recommended fixes:
1. Run: VACUUM ANALYZE customers; ANALYZE orders;
2. Create 2 indexes for fast lookups
3. Monitor cache ratio improvement

Expected improvement: 85% reduction in latency, 8x faster queries"
```

### Scenario 2: "Optimize our queries"

```
User: "How can we optimize our database?"

Bot Flow:
1. get_performance_schema(query_type='index_effectiveness')
2. check_missing_indexes()
3. analyze_slow_queries()

Bot Response:
"Found 3 optimization opportunities:

1. UNUSED INDEX: idx_old_search (created 60 days ago, 0 scans)
   Action: DROP INDEX IF EXISTS idx_old_search;

2. MISSING INDEXES: tables with >1000 sequential scans
   Action: CREATE INDEX idx_customers_email ON customers(email);
           CREATE INDEX idx_orders_product ON orders(product_id);

3. INEFFICIENT QUERIES: 5 queries doing full table scans
   Action: Modify queries to use indexed columns

Estimated improvement: 3-5x faster query execution overall"
```

### Scenario 3: "Database maintenance"

```
User: "What maintenance should we run?"

Bot Flow:
1. check_table_bloat()
2. get_performance_schema(query_type='index_effectiveness')
3. analyze_slow_queries(threshold_ms=200)

Bot Response:
"Maintenance recommendations:

URGENT (Run today):
  VACUUM ANALYZE customers;  ← 22% bloat
  REINDEX TABLE orders;       ← Index fragmentation

SCHEDULED (Weekly):
  VACUUM ANALYZE products;
  ANALYZE orders;

OPTIONAL (Monthly):
  REINDEX TABLE customers;
  REINDEX TABLE orders;

Commands to run:
  make execute-remediation action=VACUUM_ANALYZE table=customers
  make execute-remediation action=REINDEX table=orders"
```

---

## Configuration

### Enable Remediation Actions

```yaml
# In config.yaml or environment
guardrails:
  allow_remediation: true      # Enable VACUUM, ANALYZE, REINDEX
  allow_writes: false          # Disable INSERT/UPDATE/DELETE
  allow_ddl: false             # Disable CREATE/ALTER/DROP
  query_timeout_seconds: 5
  max_rows_return: 1000
```

### Available Queries

```python
# For deep analysis
analyze_slow_queries(threshold_ms=100, limit=5)

# For optimization opportunities
check_missing_indexes()

# For maintenance
check_table_bloat()

# For system diagnostics
get_performance_schema(query_type='overview|index_effectiveness|connection_stats|cache_efficiency')

# For remediation
execute_remediation(action='VACUUM|ANALYZE|VACUUM_ANALYZE|REINDEX', table='table_name')
```

---

## Key Principles

✅ **DO**:
- Always explain what metrics mean
- Provide root cause analysis
- Give actionable next steps
- Estimate performance impact
- Run analysis tools before recommending fixes
- Verify fixes with follow-up queries

❌ **DON'T**:
- Return raw JSON/metrics
- Give generic advice without analysis
- Recommend fixes without diagnosis
- Ignore context about database state
- Execute remediation without user understanding

---

## Monitoring Best Practices

1. **Daily**: Check `analyze_slow_queries()` for performance regressions
2. **Weekly**: Run `check_table_bloat()` and execute VACUUM ANALYZE if needed
3. **Monthly**: Review `check_missing_indexes()` for optimization opportunities
4. **As Needed**: Use `get_performance_schema()` for detailed diagnostics
5. **After Changes**: Verify improvements with `get_metrics()` and `analyze_slow_queries()`

---

**Last Updated**: 2026-06-09
**Status**: Advanced Monitoring Tools Active
