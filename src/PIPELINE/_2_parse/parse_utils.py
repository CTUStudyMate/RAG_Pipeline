from pipeline_config import settings


def get_batches(total_page: int, max_pages_per_batch: int | None = None) -> list[list[int]]:
    """Return zero-based inclusive page ranges for one parsing attempt."""
    if total_page <= 0:
        return []

    batch_size = (
        settings.config["max_pages_per_batch"]
        if max_pages_per_batch is None
        else max_pages_per_batch
    )
    if batch_size <= 0:
        raise ValueError("max_pages_per_batch must be greater than zero.")

    return [
        [start_page, min(start_page + batch_size - 1, total_page - 1)]
        for start_page in range(0, total_page, batch_size)
    ]
