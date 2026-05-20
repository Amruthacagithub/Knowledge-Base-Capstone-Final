# Search Indexing Guide — TechNova Platform

## Components

**Search Indexer** rebuilds document indexes from **Document Service** exports.

**Document Service** depends on **Elasticsearch Cluster** for searchable content.

## Data Flow

1. Upload lands in **Document Service**.
2. **Document Service** writes metadata to **PostgreSQL Database**.
3. **Search Indexer** depends on **Document Service** for chunk payloads.
4. **Search Indexer** writes vectors and text to **Elasticsearch Cluster**.

## Ownership

**Search Team** owns **Document Service**, **Search Indexer**, and **Elasticsearch Cluster** SLOs.
