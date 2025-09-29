#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug regex matching for IBIC2025
"""

import re
import requests
from bs4 import BeautifulSoup

response = requests.get('https://meow.elettra.eu/90/session/927-moa/index.html')
soup = BeautifulSoup(response.text, 'html.parser')
page_text = soup.get_text()

pattern = r'(MOA\w+\d+)([A-Za-z][^0-9]*?)(\d+)(.*?)(?=(?:Paper:|Cite:|MOA\w+\d+(?![0-9])|$))'
matches = re.findall(pattern, page_text, re.DOTALL)

print('Detailed analysis of matches:')
for i, match in enumerate(matches):
    paper_id, title_raw, page_num, content_raw = match
    print(f'Match {i+1}:')
    print(f'  paper_id: {paper_id}')
    print(f'  title_raw: "{title_raw}"')
    print(f'  page_num: {page_num}')
    print(f'  content_raw length: {len(content_raw)}')
    print(f'  content_raw preview: {content_raw[:200]}...')
    print()

    # Test filtering
    title = title_raw.strip()
    print(f'  Filtered title: "{title}"')
    if any(keyword in title for keyword in ['DOI:', 'About:', 'Cite:', 'reference for this paper']):
        print(f'  -> FILTERED: Contains keyword in title')
    else:
        print(f'  -> PASSED title filter')

    if len(paper_id) < 5:
        print(f'  -> FILTERED: Paper ID too short')
    else:
        print(f'  -> PASSED length filter')
    print()