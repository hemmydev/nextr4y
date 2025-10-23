#!/usr/bin/env python3
"""
Next.js Static File Analyzer & API Documentation Generator

Scans a Next.js website, downloads all static chunks, analyzes them,
and generates comprehensive documentation of API endpoints and resources.
"""

import re
import json
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import defaultdict
import argparse
from typing import Set, Dict, List, Any
import time


class NextJSAnalyzer:
    def __init__(self, base_url: str, output_dir: str = "nextjs_analysis"):
        self.base_url = base_url.rstrip('/')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.chunks_dir = self.output_dir / "chunks"
        self.chunks_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.discovered_files: Set[str] = set()
        self.api_endpoints: List[Dict[str, Any]] = []
        self.routes: List[str] = []
        self.components: Dict[str, List[str]] = defaultdict(list)
        self.env_vars: Set[str] = set()
        
    def fetch_page(self, url: str) -> str:
        """Fetch a page and return its content."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""
    
    def extract_static_files(self, html: str, page_url: str) -> Set[str]:
        """Extract all _next/static references from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        files = set()
        
        # Find script tags with src
        for script in soup.find_all('script', src=True):
            src = script['src']
            if '_next/static' in src:
                full_url = urljoin(page_url, src)
                files.add(full_url)
        
        # Find link tags (preload, etc.)
        for link in soup.find_all('link', href=True):
            href = link['href']
            if '_next/static' in href:
                full_url = urljoin(page_url, href)
                files.add(full_url)
        
        # Find inline script references
        inline_pattern = r'["\']([^"\']*_next/static/[^"\']+)["\']'
        matches = re.findall(inline_pattern, html)
        for match in matches:
            full_url = urljoin(page_url, match)
            files.add(full_url)
        
        return files
    
    def download_file(self, url: str) -> str:
        """Download a file and save it locally."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Create filename from URL
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            filename = '_'.join(path_parts[-3:])  # Take last 3 parts
            
            filepath = self.chunks_dir / filename
            filepath.write_text(response.text, encoding='utf-8')
            
            print(f"Downloaded: {filename}")
            return response.text
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return ""
    
    def analyze_javascript(self, js_content: str):
        """Analyze JavaScript content for API endpoints and routes."""
        
        # Extract API endpoints - fetch calls
        fetch_pattern = r'fetch\s*\(\s*[`"\']([^`"\']+)[`"\']'
        for match in re.finditer(fetch_pattern, js_content):
            endpoint = match.group(1)
            self.api_endpoints.append({
                'url': endpoint,
                'method': 'GET',
                'type': 'fetch'
            })
        
        # Extract axios calls
        axios_patterns = [
            r'axios\.get\s*\(\s*[`"\']([^`"\']+)[`"\']',
            r'axios\.post\s*\(\s*[`"\']([^`"\']+)[`"\']',
            r'axios\.put\s*\(\s*[`"\']([^`"\']+)[`"\']',
            r'axios\.delete\s*\(\s*[`"\']([^`"\']+)[`"\']',
        ]
        for pattern in axios_patterns:
            method = pattern.split('.')[1].split('\\')[0].upper()
            for match in re.finditer(pattern, js_content):
                endpoint = match.group(1)
                self.api_endpoints.append({
                    'url': endpoint,
                    'method': method,
                    'type': 'axios'
                })
        
        # Extract Next.js API routes
        api_route_pattern = r'["\']/(api/[^"\']+)["\']'
        for match in re.finditer(api_route_pattern, js_content):
            route = match.group(1)
            self.api_endpoints.append({
                'url': f'/{route}',
                'method': 'UNKNOWN',
                'type': 'nextjs-api'
            })
        
        # Extract page routes
        route_patterns = [
            r'href:\s*[`"\']([/][^`"\']*)[`"\']',
            r'router\.push\s*\(\s*[`"\']([/][^`"\']*)[`"\']',
            r'Link\s+.*?href=\{[`"\']([/][^`"\']*)[`"\']',
        ]
        for pattern in route_patterns:
            for match in re.finditer(pattern, js_content):
                route = match.group(1)
                if route and not route.startswith('/api'):
                    self.routes.append(route)
        
        # Extract environment variables
        env_pattern = r'process\.env\.([A-Z_][A-Z0-9_]*)'
        for match in re.finditer(env_pattern, js_content):
            self.env_vars.add(match.group(1))
        
        # Extract React components
        component_pattern = r'function\s+([A-Z][a-zA-Z0-9]*)\s*\('
        for match in re.finditer(component_pattern, js_content):
            component_name = match.group(1)
            self.components['functions'].append(component_name)
        
        # Extract class components
        class_component_pattern = r'class\s+([A-Z][a-zA-Z0-9]*)\s+extends\s+(?:React\.)?Component'
        for match in re.finditer(class_component_pattern, js_content):
            component_name = match.group(1)
            self.components['classes'].append(component_name)
    
    def combine_chunks(self) -> str:
        """Combine all downloaded chunks into a single file."""
        combined_content = []
        
        for chunk_file in sorted(self.chunks_dir.glob('*.js')):
            content = chunk_file.read_text(encoding='utf-8')
            combined_content.append(f"\n\n/* ===== {chunk_file.name} ===== */\n\n")
            combined_content.append(content)
        
        combined = ''.join(combined_content)
        combined_file = self.output_dir / "combined_chunks.js"
        combined_file.write_text(combined, encoding='utf-8')
        
        print(f"\nCombined file saved: {combined_file}")
        return combined
    
    def generate_documentation(self):
        """Generate comprehensive documentation."""
        
        # Deduplicate and organize
        unique_endpoints = {}
        for ep in self.api_endpoints:
            key = (ep['url'], ep['method'])
            if key not in unique_endpoints:
                unique_endpoints[key] = ep
        
        unique_routes = sorted(set(self.routes))
        
        # Create markdown documentation
        doc = []
        doc.append("# Next.js Application Documentation\n")
        doc.append(f"**Analyzed from:** {self.base_url}\n")
        doc.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # API Endpoints
        doc.append("## API Endpoints\n")
        if unique_endpoints:
            doc.append(f"Found {len(unique_endpoints)} unique API endpoints:\n\n")
            
            grouped = defaultdict(list)
            for ep in unique_endpoints.values():
                grouped[ep['method']].append(ep)
            
            for method in sorted(grouped.keys()):
                doc.append(f"### {method} Requests\n")
                for ep in sorted(grouped[method], key=lambda x: x['url']):
                    doc.append(f"- `{method} {ep['url']}`\n")
                    doc.append(f"  - Type: {ep['type']}\n")
                doc.append("\n")
        else:
            doc.append("No API endpoints found.\n\n")
        
        # Routes
        doc.append("## Application Routes\n")
        if unique_routes:
            doc.append(f"Found {len(unique_routes)} routes:\n\n")
            for route in unique_routes:
                doc.append(f"- `{route}`\n")
        else:
            doc.append("No routes found.\n")
        doc.append("\n")
        
        # Components
        doc.append("## React Components\n")
        total_components = len(self.components['functions']) + len(self.components['classes'])
        if total_components:
            doc.append(f"Found {total_components} components:\n\n")
            
            if self.components['functions']:
                doc.append(f"### Function Components ({len(set(self.components['functions']))})\n")
                for comp in sorted(set(self.components['functions']))[:50]:  # Limit display
                    doc.append(f"- {comp}\n")
                if len(set(self.components['functions'])) > 50:
                    doc.append(f"- ... and {len(set(self.components['functions'])) - 50} more\n")
                doc.append("\n")
            
            if self.components['classes']:
                doc.append(f"### Class Components ({len(set(self.components['classes']))})\n")
                for comp in sorted(set(self.components['classes'])):
                    doc.append(f"- {comp}\n")
                doc.append("\n")
        else:
            doc.append("No components found.\n\n")
        
        # Environment Variables
        doc.append("## Environment Variables\n")
        if self.env_vars:
            doc.append(f"Found {len(self.env_vars)} environment variable references:\n\n")
            for var in sorted(self.env_vars):
                doc.append(f"- `{var}`\n")
        else:
            doc.append("No environment variables found.\n")
        doc.append("\n")
        
        # Save documentation
        doc_file = self.output_dir / "documentation.md"
        doc_file.write_text(''.join(doc), encoding='utf-8')
        print(f"Documentation saved: {doc_file}")
        
        # Save JSON report
        report = {
            'base_url': self.base_url,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'api_endpoints': list(unique_endpoints.values()),
            'routes': unique_routes,
            'components': {
                'functions': sorted(set(self.components['functions'])),
                'classes': sorted(set(self.components['classes']))
            },
            'environment_variables': sorted(self.env_vars),
            'statistics': {
                'total_files': len(self.discovered_files),
                'api_endpoints': len(unique_endpoints),
                'routes': len(unique_routes),
                'components': total_components,
                'env_vars': len(self.env_vars)
            }
        }
        
        json_file = self.output_dir / "report.json"
        json_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"JSON report saved: {json_file}")
    
    def run(self):
        """Main execution flow."""
        print(f"Starting analysis of: {self.base_url}\n")
        
        # Fetch main page
        print("Fetching main page...")
        html = self.fetch_page(self.base_url)
        if not html:
            print("Failed to fetch main page")
            return
        
        # Extract static files
        print("Extracting static file references...")
        static_files = self.extract_static_files(html, self.base_url)
        print(f"Found {len(static_files)} static files\n")
        
        # Download and analyze each file
        print("Downloading and analyzing files...")
        all_content = []
        for i, file_url in enumerate(static_files, 1):
            print(f"[{i}/{len(static_files)}] Processing: {file_url}")
            self.discovered_files.add(file_url)
            
            content = self.download_file(file_url)
            if content:
                all_content.append(content)
                self.analyze_javascript(content)
            
            time.sleep(0.1)  # Be polite
        
        # Combine chunks
        print("\nCombining all chunks...")
        self.combine_chunks()
        
        # Generate documentation
        print("\nGenerating documentation...")
        self.generate_documentation()
        
        print("\n✅ Analysis complete!")
        print(f"   Output directory: {self.output_dir}")
        print(f"   - combined_chunks.js: All JavaScript combined")
        print(f"   - documentation.md: Markdown documentation")
        print(f"   - report.json: Machine-readable report")
        print(f"   - chunks/: Individual chunk files")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Next.js static files and generate documentation'
    )
    parser.add_argument(
        'url',
        help='Base URL of the Next.js website (e.g., https://example.com)'
    )
    parser.add_argument(
        '-o', '--output',
        default='nextjs_analysis',
        help='Output directory (default: nextjs_analysis)'
    )
    
    args = parser.parse_args()
    
    analyzer = NextJSAnalyzer(args.url, args.output)
    analyzer.run()


if __name__ == '__main__':
    main()
