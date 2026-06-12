# Engineering Certification Enablement Guide (Synthetic)

This corporate guide outlines the official certification tracks, study guidelines, and exam criteria for the engineering organization.

## Azure Developer Track (AZ-204)
The **AZ-204: Developing Solutions for Microsoft Azure** certification is required for all Cloud Engineers.
- **Primary Areas Covered:** API Development, Azure Functions, Azure Storage, Cosmos DB, App Service, and Azure Security.
- **Recommended Study Duration:** 20 hours of focused study.
- **Pass Threshold:** A target score of 75% on mock/practice assessments is required before scheduling the actual exam.
- **Reference Doc Sec 1 (Azure Functions):** Always build serverless triggers with managed identities for authentication. Avoid hardcoding secrets.
- **Reference Doc Sec 2 (Azure Storage):** Use Blob Storage Lifecycle Management to automatically archive logs older than 30 days to cool/archive tier.
- **Reference Doc Sec 3 (Cosmos DB):** Select a partition key with high cardinality to distribute data and throughput evenly.

## Azure DevOps Engineer Track (AZ-400)
The **AZ-400: Designing and Implementing Microsoft DevOps Solutions** certification is the primary track for DevOps Engineers.
- **Prerequisites:** AZ-204 (Azure Developer) or AZ-104 (Azure Administrator).
- **Primary Areas Covered:** CI/CD pipelines, monitoring, logging, infrastructure as code (IaC), containerization, and security integration.
- **Recommended Study Duration:** 25 hours.
- **Pass Threshold:** 80% on mock assessments.
- **Reference Doc Sec 4 (CI/CD Pipelines):** Always enable branch protection rules and multi-stage YAML pipelines with environment approvals.

## Azure Data Engineer Track (DP-203)
The **DP-203: Microsoft Azure Data Engineering** certification is the core track for Data Engineers.
- **Primary Areas Covered:** Data warehousing, data lakes, Synapse, Databricks, Stream Analytics, and Data Factory.
- **Recommended Study Duration:** 22 hours.
- **Pass Threshold:** 75% on mock assessments.
- **Reference Doc Sec 5 (Data Lakes):** Organize directories as hierarchical folders matching `/raw/year/month/day` for optimal analytics partitioned loads.
