# Databricks notebook source
# MAGIC %md
# MAGIC # Load Sample Data for SCA AutoFix Testing
# MAGIC
# MAGIC This notebook loads sample CSV data into Unity Catalog tables for testing the SCA AutoFix solution.
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - Upload the CSV files from `sample_data/` folder to DBFS or Volumes
# MAGIC - Have appropriate permissions to create tables in the target catalog/schema

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Configure your catalog and schema
CATALOG = "ing_hackathon"
SCHEMA = "sca_advisor"

# Path to uploaded CSV files (update based on where you uploaded them)
# Option A: DBFS path
DATA_PATH = "dbfs:/FileStore/sca_sample_data/"

# Option B: Unity Catalog Volume
# DATA_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/sample_data/"

print(f"Loading data into: {CATALOG}.{SCHEMA}")
print(f"Reading from: {DATA_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Schema (if not exists)

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load sca_findings Table

# COMMAND ----------

# Read CSV with schema inference
sca_findings_df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{DATA_PATH}sca_findings.csv")
)

# Display sample
display(sca_findings_df)

# COMMAND ----------

# Write to Unity Catalog table
sca_findings_df.write.mode("overwrite").saveAsTable(
    f"{CATALOG}.{SCHEMA}.sca_findings"
)

print(f"✅ Created table: {CATALOG}.{SCHEMA}.sca_findings")
print(f"   Rows loaded: {sca_findings_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load agent_analysis_results Table

# COMMAND ----------

agent_analysis_df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{DATA_PATH}agent_analysis_results.csv")
)

display(agent_analysis_df)

# COMMAND ----------

agent_analysis_df.write.mode("overwrite").saveAsTable(
    f"{CATALOG}.{SCHEMA}.agent_analysis_results"
)

print(f"✅ Created table: {CATALOG}.{SCHEMA}.agent_analysis_results")
print(f"   Rows loaded: {agent_analysis_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load user_decisions Table

# COMMAND ----------

user_decisions_df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{DATA_PATH}user_decisions.csv")
)

display(user_decisions_df)

# COMMAND ----------

user_decisions_df.write.mode("overwrite").saveAsTable(
    f"{CATALOG}.{SCHEMA}.user_decisions"
)

print(f"✅ Created table: {CATALOG}.{SCHEMA}.user_decisions")
print(f"   Rows loaded: {user_decisions_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load migration_analysis_results Table

# COMMAND ----------

migration_analysis_df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{DATA_PATH}migration_analysis_results.csv")
)

display(migration_analysis_df)

# COMMAND ----------

migration_analysis_df.write.mode("overwrite").saveAsTable(
    f"{CATALOG}.{SCHEMA}.migration_analysis_results"
)

print(f"✅ Created table: {CATALOG}.{SCHEMA}.migration_analysis_results")
print(f"   Rows loaded: {migration_analysis_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load generated_patches Table

# COMMAND ----------

patches_df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{DATA_PATH}generated_patches.csv")
)

display(patches_df)

# COMMAND ----------

patches_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.generated_patches")

print(f"✅ Created table: {CATALOG}.{SCHEMA}.generated_patches")
print(f"   Rows loaded: {patches_df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify All Tables

# COMMAND ----------

# List all tables in schema
tables = spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}").collect()

print("📊 Tables in schema:")
for table in tables:
    table_name = table.tableName
    count = spark.table(f"{CATALOG}.{SCHEMA}.{table_name}").count()
    print(f"   • {table_name}: {count} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Queries

# COMMAND ----------

# Query 1: Critical vulnerabilities ready for analysis
display(
    spark.sql(f"""
    SELECT repo_name, library, current_version, cvss_score, priority, status
    FROM {CATALOG}.{SCHEMA}.sca_findings
    WHERE priority = 'Critical' AND status = 'ready'
    ORDER BY cvss_score DESC, last_detected_ts DESC
""")
)

# COMMAND ----------

# Query 2: Migration complexity summary
display(
    spark.sql(f"""
    SELECT 
        migration_complexity,
        COUNT(*) as count,
        AVG(auto_fixable_percent) as avg_auto_fixable,
        AVG(estimated_effort_hours) as avg_effort_hours
    FROM {CATALOG}.{SCHEMA}.migration_analysis_results
    GROUP BY migration_complexity
    ORDER BY count DESC
""")
)

# COMMAND ----------

# Query 3: Repos with high-confidence patches available
display(
    spark.sql(f"""
    SELECT 
        v.repo_name,
        m.library,
        m.from_version,
        m.to_version,
        m.patches_high_confidence,
        m.auto_fixable_percent
    FROM {CATALOG}.{SCHEMA}.migration_analysis_results m
    JOIN {CATALOG}.{SCHEMA}.sca_findings v ON m.repo_id = v.repo_id
    WHERE m.auto_fixable_percent >= 70
    ORDER BY m.auto_fixable_percent DESC
""")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done! 🎉
# MAGIC
# MAGIC All sample data has been loaded into Unity Catalog. You can now:
# MAGIC
# MAGIC 1. **Test the MCP Agent** - Use the `get_sca_findings_from_uc` tool
# MAGIC 2. **Run the UI** - Connect the Streamlit app to these tables
# MAGIC 3. **Explore migrations** - Query the analysis results
