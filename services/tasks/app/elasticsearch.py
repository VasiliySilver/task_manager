from elasticsearch import Elasticsearch
import os

es = Elasticsearch([os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")])

def create_index():
    index_body = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "text"},
                "description": {"type": "text"},
                "status": {"type": "keyword"},
                "priority": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "user_id": {"type": "integer"}
            }
        }
    }
    es.indices.create(index="tasks", body=index_body, ignore=400)

def index_task(task):
    doc = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "tags": [tag.name for tag in task.tags],
        "user_id": task.user_id
    }
    es.index(index="tasks", id=task.id, body=doc)

def search_tasks(query, tags=None, page=1, size=10):
    body = {
        "query": {
            "bool": {
                "must": [
                    {"multi_match": {
                        "query": query,
                        "fields": ["title", "description"]
                    }}
                ]
            }
        },
        "from": (page - 1) * size,
        "size": size
    }

    if tags:
        body["query"]["bool"]["filter"] = [{"terms": {"tags": tags}}]

    result = es.search(index="tasks", body=body)
    return result
