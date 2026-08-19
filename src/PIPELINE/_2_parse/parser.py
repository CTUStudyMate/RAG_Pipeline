import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import logging
import shutil
from pipeline_config import settings
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from typing import Optional, Tuple
from typing import List
from pathlib import Path    
import json
import fitz
from src.common_utils.filename_handle import normalize_filename


logger = logging.getLogger(__name__)

def partition_document_with_docling(
    file_path: str,
    page_range: Optional[Tuple[int, int]] = None
):
    """Extract elements using Docling (IBM).
    
    Args:
        file_path: Path to document
        page_range: (start_page, end_page)
    """
    print(f"Partitioning document with Docling: {file_path}")
    
    pipeline_options = PdfPipelineOptions()
    # pipeline_options.images_scale = 2  # Adjust image resolution if needed
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True
    

    converter = DocumentConverter(
        format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options
        )
    }
    )
    

    if page_range is not None:
        print(f"Using page range: {page_range}")
        result = converter.convert(file_path, page_range=(page_range[0]+1, page_range[1]+1))
        
    else:
        print("Using full document.")
        result = converter.convert(file_path)

    if result.status is not ConversionStatus.SUCCESS:
        errors = "; ".join(
            error.error_message for error in result.errors
        ) or "no error details returned"
        raise RuntimeError(
            f"Docling conversion returned {result.status.value}: {errors}"
        )
    
    # with open("batch_debug.json", "w", encoding="utf-8") as f:
    #     json.dump(result.document.model_dump(), f, ensure_ascii=False, indent=4, default=str)
    #     f.write("\n")
    return result


def parse_pdf_document(batches: List[List[int]], file_path, storage_dir: str):

    storage_dir = Path(storage_dir)
    doc_name = normalize_filename(file_path)
    
    doc_cache_dir = storage_dir / doc_name
    doc_cache_dir.mkdir(parents=True, exist_ok=True)
    
    for batch in batches:
        result = partition_document_with_docling(
            file_path=file_path,
            page_range=(batch[0], batch[1])
        )
        
        batch_name = f"pages_{batch[0]:04d}_{batch[1]:04d}.json"
        batch_path = doc_cache_dir / batch_name
        
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(result.document.export_to_dict(), indent=2))

        
def run_parser(file_path):
    with fitz.open(file_path) as doc:
        total_page = doc.page_count

    if total_page <= 0:
        raise ValueError("The PDF does not contain any pages.")

    storage_dir = Path("./data/parsed_cache")
    doc_cache_dir = storage_dir / normalize_filename(file_path)
    max_pages_per_batch = min(
        total_page,
        settings.config["max_pages_per_batch"],
    )
    # Start a new parse run with an empty cache, but retain every batch that
    # succeeds during this run. A later failed batch must not discard earlier
    # successful work.
    shutil.rmtree(doc_cache_dir, ignore_errors=True)

    start_page = 0
    while start_page < total_page:
        end_page = min(
            start_page + max_pages_per_batch - 1,
            total_page - 1,
        )

        while end_page >= start_page:
            try:
                logger.info(
                    "Parsing %s pages %s-%s.",
                    file_path,
                    start_page + 1,
                    end_page + 1,
                )
                parse_pdf_document(
                    [[start_page, end_page]],
                    file_path,
                    storage_dir,
                )
                start_page = end_page + 1
                break
            except Exception:
                if end_page == start_page:
                    logger.exception(
                        "Parsing %s failed for page %s; stopping.",
                        file_path,
                        start_page + 1,
                    )
                    raise

                logger.exception(
                    "Parsing %s failed for pages %s-%s; retrying pages %s-%s.",
                    file_path,
                    start_page + 1,
                    end_page + 1,
                    start_page + 1,
                    end_page,
                )
                end_page -= 1
        
        
        
    
