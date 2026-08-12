.\newvenv\Scripts\python.exe -m celery -A src.workers.celery_app.celery_app worker --loglevel=INFO --pool=solo --queues=document_processing

