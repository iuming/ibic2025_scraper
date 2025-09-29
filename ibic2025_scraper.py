#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IBIC2025 Conference Web Scraper

Author: Ming Liu
Date: September 27, 2025
Description: A comprehensive web scraper for IBIC2025 conference papers and abstracts.
             Extracts paper information organized by sessions, downloads PDFs, and exports
             data in multiple formats (JSON, CSV, TXT).

Website: https://meow.elettra.eu/90/
Features:
- Session-based paper extraction
- PDF download with validation
- Multi-format data export
- Robust error handling and retry mechanisms
- Comprehensive logging
"""

import requests
from bs4 import BeautifulSoup
import os
import json
import time
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

class IBIC2025Scraper:
    """
    Web scraper for IBIC2025 conference proceedings.
    
    This scraper extracts paper information from the IBIC2025 conference website,
    organizing data by sessions and downloading available PDF files.
    """
    
    def __init__(self, base_url: str = "https://meow.elettra.eu/90/", output_dir: str = "IBIC2025_Data"):
        """
        Initialize the IBIC2025 scraper.
        
        Args:
            base_url: Base URL of the IBIC2025 conference website
            output_dir: Directory to store scraped data and PDFs
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ibic2025_scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # IBIC2025 session configuration - based on actual sessions from the website
        self.sessions_config = [
            {'id': '927-moa', 'name': 'MOA - Welcome/Overview and Commissioning', 'prefix': 'MOA'},
            {'id': '926-mob', 'name': 'MOB - Beam Charge and Current Monitors', 'prefix': 'MOB'},
            {'id': '862-moc', 'name': 'MOC - Overview and Commissioning', 'prefix': 'MOC'},
            {'id': '866-mod', 'name': 'MOD - Overview and Commissioning', 'prefix': 'MOD'},
            {'id': '1224-mopco', 'name': 'MOPCO - Monday Poster Session', 'prefix': 'MOPCO'},
            {'id': '865-mopmo', 'name': 'MOPMO - Monday Poster Session', 'prefix': 'MOPMO'},
            {'id': '878-tua', 'name': 'TUA - Data Acquisition and Processing Platforms', 'prefix': 'TUA'},
            {'id': '880-tub', 'name': 'TUB - Feedback Systems and Beam Stability', 'prefix': 'TUB'},
            {'id': '882-tuc', 'name': 'TUC - Special Talks / Machine Parameter Measurements', 'prefix': 'TUC'},
            {'id': '884-tud', 'name': 'TUD - Transverse Profile and Emittance Monitors', 'prefix': 'TUD'},
            {'id': '1225-tupco', 'name': 'TUPCO - Tuesday Poster Session', 'prefix': 'TUPCO'},
            {'id': '868-tupmo', 'name': 'TUPMO - Tuesday Poster Session', 'prefix': 'TUPMO'},
            {'id': '875-wea', 'name': 'WEA - Feedback Systems and Beam Stability / Beam Position Monitors', 'prefix': 'WEA'},
            {'id': '885-web', 'name': 'WEB - Beam Loss Monitors and Machine Protection', 'prefix': 'WEB'},
            {'id': '887-wec', 'name': 'WEC - Transverse Profile and Emittance Monitors / Machine Parameter Measurements', 'prefix': 'WEC'},
            {'id': '889-wed', 'name': 'WED - Beam Position Monitors', 'prefix': 'WED'},
            {'id': '1226-wepco', 'name': 'WEPCO - Wednesday Poster Session', 'prefix': 'WEPCO'},
            {'id': '869-wepmo', 'name': 'WEPMO - Wednesday Poster Session', 'prefix': 'WEPMO'},
            {'id': '870-tha', 'name': 'THA - Longitudinal Diagnostics and Synchronization', 'prefix': 'THA'},
            {'id': '874-thb', 'name': 'THB - Longitudinal Diagnostics and Synchronization / Special Talks / Closing Session', 'prefix': 'THB'}
        ]
        
        # Initialize directories and statistics
        self.create_directories()
        self.stats = {'total_papers': 0, 'downloaded_pdfs': 0, 'errors': 0, 'sessions_processed': 0}
    
    def create_directories(self):
        """Create necessary directory structure for output files."""
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "PDFs").mkdir(exist_ok=True)
        (self.output_dir / "Sessions").mkdir(exist_ok=True)
        (self.output_dir / "Debug").mkdir(exist_ok=True)
        self.logger.info(f"Created output directory: {self.output_dir}")
    
    def safe_filename(self, filename: str, max_length: int = 120) -> str:
        """
        Convert filename to safe filesystem name.
        
        Args:
            filename: Original filename
            max_length: Maximum allowed filename length
            
        Returns:
            Safe filename string
        """
        if not filename:
            return "unknown"
        
        # Remove invalid characters and special characters that can cause issues
        filename = re.sub(r'[<>:"/\\|?*\r\n\[\](){}]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename)
        filename = filename.strip(' ._')
        
        # Truncate if too long
        if len(filename) > max_length:
            filename = filename[:max_length].rsplit(' ', 1)[0]
        
        return filename or "unknown"
    
    def get_page_content(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Get webpage content with retry mechanism.
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
            
        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                self.logger.warning(f"Failed to fetch page (attempt {attempt + 1}/{retries}) {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"Final failure fetching page {url}: {e}")
                    self.stats['errors'] += 1
        return None
    
    def extract_papers_from_session(self, soup: BeautifulSoup, session_prefix: str) -> List[Dict[str, Any]]:
        """
        Extract paper information from a session page.
        
        Args:
            soup: BeautifulSoup object of the session page
            session_prefix: Session prefix (e.g., 'TUOA', 'TUP')
            
        Returns:
            List of paper dictionaries
        """
        papers = []
        page_text = soup.get_text()
        
        # Save debug information
        debug_file = self.output_dir / "Debug" / f"{session_prefix}_page_text.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(page_text)
        
        # For IBIC2025, find all paper IDs that are followed by content (not metadata)
        # Paper IDs appear at the start of each paper, followed immediately by the title
        paper_id_pattern = rf'({session_prefix}\w+\d+)(?=[A-Za-z])'
        paper_ids = re.findall(paper_id_pattern, page_text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paper_ids = []
        for pid in paper_ids:
            if pid not in seen:
                seen.add(pid)
                unique_paper_ids.append(pid)
        
        paper_ids = unique_paper_ids
        
        self.logger.info(f"Session {session_prefix} found {len(paper_ids)} unique paper IDs: {paper_ids}")
        
        # Process each paper by extracting content between paper IDs
        for i, paper_id in enumerate(paper_ids):
            # Find the start position of this paper ID
            start_pos = page_text.find(paper_id)
            if start_pos == -1:
                continue
                
            # Find the end position (next paper ID or end of text)
            if i < len(paper_ids) - 1:
                next_paper_id = paper_ids[i + 1]
                end_pos = page_text.find(next_paper_id, start_pos + len(paper_id))
                if end_pos == -1:
                    end_pos = len(page_text)
            else:
                end_pos = len(page_text)
            
            # Extract the content for this paper
            paper_content = page_text[start_pos:end_pos].strip()
            
            # Extract paper details
            paper_info = self.extract_paper_details_ibic(paper_id, paper_content)
            
            if paper_info:
                papers.append(paper_info)
                self.logger.info(f"  ✓ {paper_id}: {paper_info['title'][:50]}...")
        
        return papers
    
    def extract_paper_details(self, paper_id: str, title_raw: str, page_num: str, content: str) -> Dict[str, Any]:
        """
        Extract detailed information for a single paper.
        
        Args:
            paper_id: Paper ID (e.g., 'TUOA01')
            title_raw: Raw paper title
            page_num: Page number
            content: Raw content text
            
        Returns:
            Dictionary containing paper information
        """
        paper_info = {
            'paper_id': paper_id,
            'title': title_raw,
            'authors': [],
            'institutions': [],
            'abstract': '',
            'pdf_url': urljoin(self.base_url, f"pdf/{paper_id}.pdf"),
            'doi': f"https://doi.org/10.18429/JACoW-IBIC2025-{paper_id}",
            'received_date': '',
            'accepted_date': '',
            'page_number': page_num,
            'pdf_available': False
        }
        
        # Analyze content to extract abstract and author information
        lines = content.split('\n')
        abstract_lines = []
        author_section = ""
        
        # Find author section (usually at the end, short lines with uppercase letters)
        author_started = False
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is the start of author information
            if (not author_started and 
                (re.match(r'^[A-Z]\.\s+[A-Z][a-z]+', line) or 
                 (len(line.split()) <= 8 and any(c.isupper() for c in line[:5])))):
                author_started = True
                author_section = line
                continue
                
            # Continue collecting author information
            if author_started:
                if any(keyword in line for keyword in ['Paper:', 'DOI:', 'About:', 'Received:', 'Cite:']):
                    # Stop when encountering metadata
                    break
                author_section += " " + line
            else:
                # Still in abstract section
                if len(line) > 20:  # Lines long enough to be abstract content
                    abstract_lines.append(line)
        
        if abstract_lines:
            paper_info['abstract'] = ' '.join(abstract_lines)
        
        # Parse author and institution information
        if author_section:
            self.parse_authors_and_institutions(author_section, paper_info)
        
        # Extract date information from content
        received_match = re.search(r'Received:\s*(\d{1,2}\s+\w+\s+\d{4})', content)
        if received_match:
            paper_info['received_date'] = received_match.group(1)
            
        accepted_match = re.search(r'Accepted:\s*(\d{1,2}\s+\w+\s+\d{4})', content)
        if accepted_match:
            paper_info['accepted_date'] = accepted_match.group(1)
        
        # Check PDF availability
        paper_info['pdf_available'] = self.check_pdf_exists(paper_info['pdf_url'])
        
        return paper_info
    
    def parse_authors_and_institutions(self, author_text: str, paper_info: Dict[str, Any]):
        """
        Parse author and institution information from text.
        
        Args:
            author_text: Raw author text
            paper_info: Paper information dictionary to update
        """
        # Split by double or more spaces to separate authors from institutions
        parts = re.split(r'\s{2,}', author_text)
        
        if len(parts) >= 2:
            author_part = parts[0].strip()
            institution_part = ' '.join(parts[1:]).strip()
            
            # Parse authors (usually comma-separated)
            if author_part:
                authors = [a.strip() for a in author_part.split(',') if a.strip()]
                paper_info['authors'] = authors
            
            # Parse institutions
            if institution_part:
                # Institutions may be separated by semicolons or special characters
                institutions = [inst.strip() for inst in re.split(r'[;,](?=[A-Z])', institution_part) if inst.strip()]
                paper_info['institutions'] = institutions
        else:
            # If no clear separation, try simple parsing
            text = author_text.strip()
            if text:
                # Look for obvious institution keywords
                institution_keywords = ['University', 'Laboratory', 'Institute', 'Center', 'Corporation', 
                                      'School', 'Facility', 'Source', 'Accelerator', 'National', 'Synchrotron']
                
                if any(keyword in text for keyword in institution_keywords):
                    paper_info['institutions'].append(text)
                else:
                    # Likely author names
                    authors = [a.strip() for a in text.split(',') if a.strip()]
                    paper_info['authors'] = authors
    
    def extract_paper_details_ibic(self, paper_id: str, content: str) -> Dict[str, Any]:
        """
        Extract detailed information for a single IBIC2025 paper.
        
        Args:
            paper_id: Paper ID (e.g., 'MOAI01')
            content: Raw content text for the entire paper
            
        Returns:
            Dictionary containing paper information
        """
        paper_info = {
            'paper_id': paper_id,
            'title': '',
            'authors': [],
            'institutions': [],
            'abstract': '',
            'pdf_url': urljoin(self.base_url, f"pdf/{paper_id}.pdf"),
            'doi': f"https://doi.org/10.18429/JACoW-IBIC2025-{paper_id}",
            'received_date': '',
            'accepted_date': '',
            'page_number': '',
            'pdf_available': False
        }
        
        # Remove the paper ID from the beginning
        content = content[len(paper_id):].strip()
        
        # Remove "Cite: reference..." and everything after it
        cite_pos = content.find('Cite:')
        if cite_pos != -1:
            content = content[:cite_pos].strip()
        
        # Remove metadata patterns
        metadata_patterns = [
            r'Paper:\s*' + re.escape(paper_id),
            r'DOI:\s*reference for this paper:',
            r'About:\s*Received:',
            r'Received:\s*\d{1,2}\s+\w+\s+\d{4}',
            r'Revised:\s*\d{1,2}\s+\w+\s+\d{4}',
            r'Accepted:\s*\d{1,2}\s+\w+\s+\d{4}',
            r'Issue date:\s*\d{1,2}\s+\w+\s+\d{4}'
        ]
        
        for pattern in metadata_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE).strip()
        
        # Extract author and institution information
        # Look for patterns like "Author Name  Institution Name"
        author_institution_matches = re.findall(r'([A-Z][a-zA-Z\s]+(?:\s+[A-Z]\.)*)\s{2,}([A-Z][a-zA-Z\s]*(?:University|Laboratory|Institute|Center|National|Facility|Source|Accelerator|Synchrotron|Cockcroft|Elettra|ESRF|DESY|SLAC|LANL|BNL|CERN|KEK|Spring-8|Organization|Research|Technology|Council|College|School|Department|Division)[a-zA-Z\s]*(?:\([^)]*\))*)', content)
        
        authors = []
        institutions = []
        
        for author_match, institution_match in author_institution_matches:
            author_match = author_match.strip()
            institution_match = institution_match.strip()
            
            # Clean up author name
            author_match = re.sub(r'\s+', ' ', author_match).strip()
            if author_match and len(author_match.split()) <= 5:  # Reasonable name length
                authors.append(author_match)
            
            # Clean up institution name
            institution_match = re.sub(r'\s+', ' ', institution_match).strip()
            if institution_match:
                institutions.append(institution_match)
            
            # Remove this match from content
            content = content.replace(f"{author_match}  {institution_match}", "").strip()
        
        # Also look for simpler author patterns at the end
        author_only_patterns = [
            r'\b([A-Z]\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[A-Z]\.)\b'
        ]
        
        for pattern in author_only_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                match = match.strip()
                if match not in authors and len(match.split()) <= 4:
                    authors.append(match)
                    content = content.replace(match, "").strip()
        
        paper_info['authors'] = list(set(authors))  # Remove duplicates
        paper_info['institutions'] = list(set(institutions))  # Remove duplicates
        
        # Now extract title and abstract from remaining content
        content = content.strip()
        
        if not content:
            return paper_info
        
        # For IBIC2025, titles are typically followed by the abstract without clear separation
        # We'll use heuristics to split them
        
        # Look for common title-ending patterns
        title_end_patterns = [
            r'([A-Z][^.!?]*?:)',  # Title ending with colon
            r'([A-Z][^.!?]*?\.)',  # Title ending with period
            r'([A-Z][^.!?]*?!)',  # Title ending with exclamation
            r'([A-Z][^.!?]*?\?)',  # Title ending with question
        ]
        
        title = ""
        abstract = content
        
        for pattern in title_end_patterns:
            match = re.search(pattern, content)
            if match:
                potential_title = match.group(1).strip()
                # Check if this looks like a reasonable title
                if 20 <= len(potential_title) <= 150 and not any(word in potential_title.lower() for word in ['the', 'a', 'an', 'this', 'these', 'those']):
                    # Additional check: title should not contain sentence connectors
                    if not any(connector in potential_title.lower() for connector in [' however', ' therefore', ' thus', ' hence', ' consequently']):
                        title = re.sub(r'[.:!?]$', '', potential_title).strip()
                        abstract_start = match.end()
                        abstract = content[abstract_start:].strip()
                        break
        
        # If no pattern matched, try to find a natural break based on abstract starters
        if not title:
            # Look for the first occurrence of common abstract starters
            abstract_starters = ['In this', 'This paper', 'The paper', 'We present', 'This work', 'In the', 'The system', 'A new', 'An improved', 'Recent', 'During', 'Since', 'As part', 'One of', 'Among the', 'In March', 'In April', 'In May', 'In June', 'In July', 'In August', 'In September', 'In October', 'In November', 'In December', 'In 2025', 'In 2024', 'In 2023']
            
            best_pos = -1
            best_starter = ""
            
            for starter in abstract_starters:
                pos = content.find(starter)
                if pos > 30 and pos < 120:  # Reasonable title length
                    if best_pos == -1 or pos < best_pos:
                        best_pos = pos
                        best_starter = starter
            
            if best_pos != -1:
                title = content[:best_pos].strip()
                # Clean up title - remove trailing punctuation
                title = re.sub(r'[.:!?;,]$', '', title).strip()
                abstract = content[best_pos:].strip()
            
            # Last resort: split at reasonable length
            if not title and len(content) > 80:
                # Find a break point around 80-120 characters, preferring word boundaries
                break_point = content.rfind(' ', 80, 120)
                if break_point == -1:
                    break_point = 100
                title = content[:break_point].strip()
                # Clean up title
                title = re.sub(r'[.:!?;,]$', '', title).strip()
                abstract = content[break_point:].strip()
        
        paper_info['title'] = title if title else content[:100].strip()
        paper_info['abstract'] = abstract if abstract != content else (content[100:].strip() if len(content) > 100 else "")
        
        # Clean up title
        paper_info['title'] = re.sub(r'[.:;]$', '', paper_info['title']).strip()
        
        # Clean up abstract
        paper_info['abstract'] = paper_info['abstract'].strip()
        if paper_info['abstract'].startswith('.'):
            paper_info['abstract'] = paper_info['abstract'][1:].strip()
        
        # Check PDF availability
        paper_info['pdf_available'] = self.check_pdf_exists(paper_info['pdf_url'])
        
        return paper_info
    
    def check_pdf_exists(self, pdf_url: str) -> bool:
        """
        Check if PDF file exists and is accessible.
        
        Args:
            pdf_url: URL of the PDF file
            
        Returns:
            True if PDF exists and is accessible
        """
        try:
            response = self.session.head(pdf_url, timeout=10)
            return response.status_code == 200 and 'pdf' in response.headers.get('content-type', '').lower()
        except:
            return False
    
    def scrape_session(self, session: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Scrape all papers from a single session.
        
        Args:
            session: Session configuration dictionary
            
        Returns:
            List of paper dictionaries
        """
        self.logger.info(f"Scraping session: {session['name']}")
        
        soup = self.get_page_content(session['url'])
        if not soup:
            return []
        
        papers = self.extract_papers_from_session(soup, session['prefix'])
        
        self.stats['total_papers'] += len(papers)
        self.stats['sessions_processed'] += 1
        
        self.logger.info(f"Session {session['prefix']} results: {len(papers)} papers")
        
        # Display found papers
        for i, paper in enumerate(papers):
            pdf_status = "✓" if paper['pdf_available'] else "✗"
            self.logger.info(f"  {i+1}. {paper['paper_id']}: {paper['title'][:50]}... [PDF:{pdf_status}]")
        
        return papers
    
    def download_pdf(self, pdf_url: str, paper_info: Dict[str, Any], session_name: str) -> bool:
        """
        Download PDF file for a paper.
        
        Args:
            pdf_url: URL of the PDF file
            paper_info: Paper information dictionary
            session_name: Name of the session
            
        Returns:
            True if download successful
        """
        if not paper_info.get('pdf_available', False):
            return False
            
        try:
            session_pdf_dir = self.output_dir / "PDFs" / self.safe_filename(session_name)
            session_pdf_dir.mkdir(exist_ok=True)
            
            filename = f"{paper_info['paper_id']} - {paper_info['title']}"
            safe_name = self.safe_filename(filename)
            if not safe_name.endswith('.pdf'):
                safe_name += '.pdf'
            
            filepath = session_pdf_dir / safe_name
            
            if filepath.exists():
                self.logger.info(f"PDF already exists, skipping: {safe_name}")
                return True
            
            response = self.session.get(pdf_url, stream=True, timeout=60)
            response.raise_for_status()
            
            content_length = int(response.headers.get('content-length', 0))
            if content_length > 0 and content_length < 100:  # Skip obviously wrong small files
                self.logger.warning(f"PDF file too small ({content_length} bytes), skipping: {paper_info['paper_id']}")
                return False
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.stats['downloaded_pdfs'] += 1
            self.logger.info(f"✅ Downloaded PDF: {safe_name} ({content_length} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download PDF {pdf_url}: {e}")
            self.stats['errors'] += 1
            return False
    
    def save_session_data(self, session: Dict[str, str], papers: List[Dict[str, Any]]):
        """
        Save session data to files in multiple formats.
        
        Args:
            session: Session configuration dictionary
            papers: List of paper dictionaries
        """
        session_dir = self.output_dir / "Sessions" / self.safe_filename(session['name'])
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON format
        json_file = session_dir / "papers_data.json"
        session_data = {
            'session_info': session,
            'papers': papers,
            'paper_count': len(papers),
            'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # CSV format
        self.save_session_csv(session_dir, papers, session)
        
        # Text format
        self.save_session_txt(session_dir, session, papers)
        
        self.logger.info(f"Saved session data: {session['name']} ({len(papers)} papers)")
    
    def save_session_csv(self, session_dir: Path, papers: List[Dict[str, Any]], session: Dict[str, str]):
        """Save session data in CSV format."""
        import csv
        
        csv_file = session_dir / "papers_data.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            if not papers:
                return
                
            fieldnames = ['session_name', 'paper_id', 'title', 'authors', 'institutions', 'abstract', 
                         'pdf_url', 'pdf_available', 'doi', 'page_number', 'received_date', 'accepted_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for paper in papers:
                row = {
                    'session_name': session['name'],
                    **paper
                }
                row['authors'] = '; '.join(paper['authors'])
                row['institutions'] = '; '.join(paper['institutions'])
                writer.writerow(row)
    
    def save_session_txt(self, session_dir: Path, session: Dict[str, str], papers: List[Dict[str, Any]]):
        """Save session data in text format."""
        txt_file = session_dir / "papers_summary.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Session: {session['name']}\n")
            f.write(f"Session ID: {session['id']}\n")
            f.write(f"URL: {session['url']}\n")
            f.write(f"Scrape time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Paper count: {len(papers)}\n")
            available_pdfs = sum(1 for p in papers if p.get('pdf_available', False))
            f.write(f"Available PDFs: {available_pdfs}/{len(papers)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, paper in enumerate(papers, 1):
                pdf_status = "✓ Available" if paper.get('pdf_available', False) else "✗ Not available"
                f.write(f"{i}. Paper ID: {paper['paper_id']}\n")
                f.write(f"   Title: {paper['title']}\n")
                if paper['authors']:
                    f.write(f"   Authors: {', '.join(paper['authors'])}\n")
                if paper['institutions']:
                    f.write(f"   Institutions: {'; '.join(paper['institutions'])}\n")
                f.write(f"   Page: {paper.get('page_number', 'N/A')}\n")
                f.write(f"   PDF Status: {pdf_status}\n")
                f.write(f"   PDF URL: {paper['pdf_url']}\n")
                if paper['doi']:
                    f.write(f"   DOI: {paper['doi']}\n")
                if paper['received_date']:
                    f.write(f"   Received: {paper['received_date']}\n")
                if paper['accepted_date']:
                    f.write(f"   Accepted: {paper['accepted_date']}\n")
                if paper['abstract']:
                    abstract_preview = paper['abstract'][:300] + '...' if len(paper['abstract']) > 300 else paper['abstract']
                    f.write(f"   Abstract: {abstract_preview}\n")
                f.write("-" * 60 + "\n")
    
    def create_final_summary(self, all_sessions_data: List[Dict]):
        """
        Create final summary report of all scraped data.
        
        Args:
            all_sessions_data: List of all session data dictionaries
        """
        # Calculate statistics
        total_available_pdfs = sum(
            sum(1 for paper in session_data['papers'] if paper.get('pdf_available', False))
            for session_data in all_sessions_data
        )
        
        # Text summary
        summary_file = self.output_dir / "IBIC2025_Final_Report.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("IBIC2025 Conference Complete Scraping Report\n")
            f.write("=" * 60 + "\n")
            f.write(f"Scrape completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Sessions processed: {self.stats['sessions_processed']}\n")
            f.write(f"Total papers: {self.stats['total_papers']}\n")
            f.write(f"Available PDFs: {total_available_pdfs}\n")
            f.write(f"Successfully downloaded PDFs: {self.stats['downloaded_pdfs']}\n")
            f.write(f"Download success rate: {(self.stats['downloaded_pdfs']/total_available_pdfs*100):.1f}%\n" if total_available_pdfs > 0 else "Download success rate: 0%\n")
            f.write(f"Errors: {self.stats['errors']}\n\n")
            
            f.write("Session detailed statistics:\n")
            f.write("-" * 50 + "\n")
            for session_data in all_sessions_data:
                session = session_data['session_info']
                papers = session_data['papers']
                available_pdfs = sum(1 for p in papers if p.get('pdf_available', False))
                
                f.write(f"Session: {session['name']}\n")
                f.write(f"   Papers: {len(papers)}\n")
                f.write(f"   Available PDFs: {available_pdfs}\n")
                f.write(f"   URL: {session['url']}\n")
                
                if papers:
                    f.write("   Paper list:\n")
                    for paper in papers:
                        pdf_icon = "PDF" if paper.get('pdf_available', False) else "---"
                        f.write(f"     [{pdf_icon}] {paper['paper_id']}: {paper['title'][:60]}...\n")
                f.write("\n")
        
        # JSON index
        master_json = self.output_dir / "IBIC2025_Complete_Index.json"
        with open(master_json, 'w', encoding='utf-8') as f:
            json.dump({
                'scrape_info': {
                    'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sessions_processed': self.stats['sessions_processed'],
                    'total_papers': self.stats['total_papers'],
                    'available_pdfs': total_available_pdfs,
                    'downloaded_pdfs': self.stats['downloaded_pdfs'],
                    'download_success_rate': f"{(self.stats['downloaded_pdfs']/total_available_pdfs*100):.1f}%" if total_available_pdfs > 0 else "0%",
                    'errors': self.stats['errors']
                },
                'sessions': all_sessions_data
            }, f, ensure_ascii=False, indent=2)
        
        # Create master CSV
        self.create_master_csv(all_sessions_data)
    
    def create_master_csv(self, all_sessions_data: List[Dict]):
        """Create master CSV file containing all papers."""
        import csv
        
        csv_file = self.output_dir / "IBIC2025_All_Papers.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['session_name', 'session_id', 'paper_id', 'title', 'authors', 'institutions', 
                         'abstract', 'pdf_url', 'pdf_available', 'doi', 'page_number', 'received_date', 'accepted_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for session_data in all_sessions_data:
                session_info = session_data['session_info']
                for paper in session_data['papers']:
                    row = {
                        'session_name': session_info['name'],
                        'session_id': session_info['id'],
                        **paper
                    }
                    row['authors'] = '; '.join(paper['authors'])
                    row['institutions'] = '; '.join(paper['institutions'])
                    writer.writerow(row)
    
    def run(self, test_mode: bool = False, skip_pdf_download: bool = False):
        """
        Run the main scraping process.
        
        Args:
            test_mode: If True, only process first 3 sessions for testing
            skip_pdf_download: If True, skip PDF downloading to speed up testing
            
        Returns:
            List of all session data
        """
        self.logger.info("Starting IBIC2025 conference data scraping")
        start_time = time.time()
        
        try:
            sessions = []
            for session_info in self.sessions_config:
                sessions.append({
                    'id': session_info['id'],
                    'name': session_info['name'],
                    'url': urljoin(self.base_url, f"session/{session_info['id']}/index.html"),
                    'prefix': session_info['prefix']
                })
            
            self.logger.info(f"Prepared to process {len(sessions)} sessions")
            
            if test_mode:
                sessions = sessions[:3]  # Test with first 3 sessions (MOIG, MOKG, MOAG)
                self.logger.info(f"Test mode: processing first 3 sessions")
            
            all_sessions_data = []
            
            # Process each session
            for i, session in enumerate(sessions, 1):
                self.logger.info(f"\nProcessing session {i}/{len(sessions)}: {session['name']}")
                
                try:
                    papers = self.scrape_session(session)
                    
                    if papers:
                        self.save_session_data(session, papers)
                        
                        # Download PDF files (unless skipped)
                        if not skip_pdf_download:
                            available_pdfs = [p for p in papers if p.get('pdf_available', False)]
                            pdf_downloaded = 0
                            
                            for paper in available_pdfs:
                                success = self.download_pdf(paper['pdf_url'], paper, session['name'])
                                if success:
                                    pdf_downloaded += 1
                                time.sleep(1)  # Avoid too frequent requests
                            
                            self.logger.info(f"✅ Session completed: {len(papers)} papers, {len(available_pdfs)} available PDFs, {pdf_downloaded} downloaded successfully")
                        else:
                            available_pdfs = [p for p in papers if p.get('pdf_available', False)]
                            self.logger.info(f"✅ Session completed: {len(papers)} papers, {len(available_pdfs)} available PDFs (download skipped)")
                    else:
                        self.logger.info(f"⚠️ Session {session['prefix']} found no papers")
                    
                    all_sessions_data.append({
                        'session_info': session,
                        'papers': papers,
                        'paper_count': len(papers)
                    })
                    
                    time.sleep(2)  # Rest between sessions
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing session {session['name']}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Create final report
            self.create_final_summary(all_sessions_data)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"\n🎉 Scraping completed! Time elapsed: {elapsed_time:.2f} seconds")
            self.logger.info(f"📊 Final statistics:")
            self.logger.info(f"  ✅ Sessions processed: {self.stats['sessions_processed']}")
            self.logger.info(f"  📄 Total papers: {self.stats['total_papers']}")
            self.logger.info(f"  💾 PDFs downloaded: {self.stats['downloaded_pdfs']}")
            self.logger.info(f"  ❌ Errors: {self.stats['errors']}")
            
            return all_sessions_data
            
        except Exception as e:
            self.logger.error(f"Critical error during scraping process: {e}")
            raise


def main():
    """Main function to run the IBIC2025 scraper."""
    print("IBIC2025 Conference Web Scraper")
    print("=" * 60)
    print("Comprehensive scraper for IBIC2025 conference papers")
    print("Author: Ming Liu")
    print()
    
    scraper = IBIC2025Scraper()
    
    try:
        print("Starting test mode...")
        results = scraper.run(test_mode=True, skip_pdf_download=True)
        
        print("\n" + "="*60)
        print("Test completed successfully!")
        
        # Ask if user wants to continue with full scraping
        print("\nWould you like to continue with full scraping of all 20 sessions?")
        choice = input("Enter 'y' to continue with full scraping, any other key to exit: ").lower().strip()
        
        if choice == 'y':
            print("\nStarting full scraping...")
            results = scraper.run(test_mode=False, skip_pdf_download=False)
            
            print("\n" + "="*60)
            print("Full scraping completed successfully!")
            print(f"Output directory: {scraper.output_dir}")
            print("\nMain output files:")
            print("  📊 IBIC2025_Final_Report.txt - Complete scraping report")
            print("  📈 IBIC2025_All_Papers.csv - All papers Excel table")
            print("  🗂️ IBIC2025_Complete_Index.json - Complete data index")
            print("  📁 Sessions/ - Session-categorized detailed data")
            print("  📄 PDFs/ - Downloaded PDF files (categorized by session)")
            print("  🔍 Debug/ - Debug information and page content")
            print("\n💡 Each session contains JSON, CSV, TXT format data")
        
    except KeyboardInterrupt:
        print("\n⏹️ User interrupted scraping")
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")


if __name__ == "__main__":
    main()