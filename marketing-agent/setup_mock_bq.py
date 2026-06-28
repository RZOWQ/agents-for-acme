import sys
from google.cloud import bigquery
from google.api_core.exceptions import Conflict

def setup_mock_data():
    project_id = "civil-epigram-499906-f4"
    client = bigquery.Client(project=project_id)

    # 1. Create Dataset
    dataset_id = f"{project_id}.acme_media"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    try:
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {dataset_id}")
    except Conflict:
        print(f"Dataset {dataset_id} already exists")

    # 2. Create Table
    table_id = f"{dataset_id}.podcast_performance"
    schema = [
        bigquery.SchemaField("episode_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("views", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("likes", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("shares", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("sentiment_score", "FLOAT", mode="REQUIRED"),
    ]
    table = bigquery.Table(table_id, schema=schema)
    try:
        table = client.create_table(table)
        print(f"Created table {table_id}")
    except Conflict:
        print(f"Table {table_id} already exists")

    # 3. Insert Mock Data
    rows_to_insert = [
        {"episode_id": "EP001", "title": "The Future of Renewable Energy", "category": "Energy", "views": 12000, "likes": 950, "shares": 340, "sentiment_score": 0.88},
        {"episode_id": "EP002", "title": "Exploring AI & Deep Learning", "category": "AI", "views": 35000, "likes": 4200, "shares": 1200, "sentiment_score": 0.92},
        {"episode_id": "EP003", "title": "Designing Sustainable Homes", "category": "Sustainability", "views": 8000, "likes": 450, "shares": 180, "sentiment_score": 0.81},
        {"episode_id": "EP004", "title": "Climate Change Impact", "category": "Sustainability", "views": 15000, "likes": 1100, "shares": 400, "sentiment_score": 0.79},
    ]

    errors = client.insert_rows_json(table_id, rows_to_insert)
    if not errors:
        print("Mock data loaded successfully.")
    else:
        print(f"Errors occurred while inserting mock data: {errors}")

if __name__ == "__main__":
    setup_mock_data()
