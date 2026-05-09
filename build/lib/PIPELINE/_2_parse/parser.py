import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from typing import Optional, Tuple
from typing import List
from pathlib import Path    
import json
import fitz
from src.PIPELINE._2_parse.parse_utils import get_batches

from src.common_utils.filename_handle import normalize_filename

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
    doc = fitz.open(file_path)
    total_page = doc.page_count
    batches = get_batches(total_page)
    parse_pdf_document(batches, file_path, "./data/parsed_cache")        
        
        
        
    