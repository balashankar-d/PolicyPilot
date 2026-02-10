"""PDF ingestion and preprocessing module."""

import fitz  # PyMuPDF - note: package name is PyMuPDF but import is fitz
import pdfplumber
import re
import logging
from typing import List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF text extraction and preprocessing."""
    
    def __init__(self):
        self.logger = logger
    
    def extract_text_pymupdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF (fitz)."""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page in doc:
                text = page.get_text()
                full_text += text + "\n"
            
            doc.close()
            return full_text
        except Exception as e:
            self.logger.error(f"Error extracting text with PyMuPDF: {str(e)}")
            raise
    
    def extract_text_pdfplumber(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber as fallback."""
        try:
            full_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            
            return full_text
        except Exception as e:
            self.logger.error(f"Error extracting text with pdfplumber: {str(e)}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text by removing excess whitespace and fixing encoding issues."""
        try:
            # Remove excess whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove common PDF artifacts
            text = re.sub(r'\x0c', ' ', text)  # Form feed characters
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)  # Control characters
            
            # Normalize line breaks
            text = text.replace('\n\n', '\n').replace('\r\n', '\n')
            
            # Strip leading/trailing whitespace
            text = text.strip()
            
            return text
        except Exception as e:
            self.logger.error(f"Error cleaning text: {str(e)}")
            return text
    
    def process_pdf(self, pdf_path: str) -> str:
        """
        Process a PDF file and return cleaned text.
        Tries PyMuPDF first, falls back to pdfplumber if needed.
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Try PyMuPDF first
            text = self.extract_text_pymupdf(pdf_path)
            if not text.strip():
                self.logger.warning("PyMuPDF returned empty text, trying pdfplumber")
                text = self.extract_text_pdfplumber(pdf_path)
            
            # Clean the extracted text
            cleaned_text = self.clean_text(text)
            
            if not cleaned_text.strip():
                raise ValueError("No text could be extracted from the PDF")
            
            self.logger.info(f"Successfully extracted {len(cleaned_text)} characters from {pdf_path}")
            return cleaned_text
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
