#!/usr/bin/env python3
"""
Documentation Change Tracker
Analyzes git commits to generate monthly documentation update summaries.
"""

import subprocess
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import argparse

# Product categories mapping
CATEGORIES = {
    'app_perf': {
        'name': 'Application Performance',
        'products': {
            'argo-smart-routing': 'Argo Smart Routing',
            'automatic-platform-optimization': 'Automatic Platform Optimization',
            'cache': 'Cache',
            'cloudflare-for-platforms': 'Cloudflare for SaaS',
            'data-localization': 'Data Localization',
            'dns': 'DNS',
            'health-checks': 'Health Checks',
            'load-balancing': 'Load Balancing',
            'logs': 'Logs',
            'rules': 'Rules',
            'speed': 'Speed',
            'ssl': 'SSL/TLS',
            'version-management': 'Version Management',
            '1.1.1.1': '1.1.1.1',
        }
    },
    'app_sec': {
        'name': 'Application Security',
        'products': {
            'api-shield': 'API Shield',
            'bots': 'Bot Management',
            'cloudflare-challenges': 'Cloudflare Challenges',
            'ddos-protection': 'DDoS Protection',
            'firewall': 'Firewall',
            'log-explorer': 'Log Explorer',
            'page-shield': 'Page Shield',
            'ruleset-engine': 'Ruleset Engine',
            'security': 'Security',
            'security-center': 'Security Center',
            'smart-shield': 'Smart Shield',
            'turnstile': 'Turnstile',
            'waf': 'WAF',
            'waiting-room': 'Waiting Room',
        }
    },
    'cf1': {
        'name': 'Cloudflare One',
        'products': {
            'browser-rendering': 'Browser Rendering',
            'byoip': 'BYOIP',
            'china-network': 'China Network',
            'client-ip-geolocation': 'Client IP Geolocation',
            'cloudflare-one': 'Cloudflare One',
            'email-security': 'Email Security',
            'magic-cloud-networking': 'Magic Cloud Networking',
            'magic-firewall': 'Magic Firewall',
            'magic-network-monitoring': 'Magic Network Monitoring',
            'magic-transit': 'Magic Transit',
            'magic-wan': 'Magic WAN',
            'network': 'Network',
            'network-error-logging': 'Network Error Logging',
            'network-interconnect': 'Network Interconnect',
            'spectrum': 'Spectrum',
            'warp-client': 'WARP Client',
        }
    },
    'platform': {
        'name': 'Platform',
        'products': {
            'analytics': 'Analytics',
            'billing': 'Billing',
            'notifications': 'Notifications',
            'pulumi': 'Pulumi',
            'radar': 'Radar',
            'registrar': 'Registrar',
            'tenant': 'Tenant',
            'time-services': 'Time Services',
        }
    },
    'dev_plat': {
        'name': 'Developer Platform',
        'products': {
            'agents': 'Agents',
            'ai-crawl-control': 'AI Crawl Control',
            'ai-gateway': 'AI Gateway',
            'ai-search': 'AI Search',
            'containers': 'Containers',
            'd1': 'D1',
            'dmarc-management': 'DMARC Management',
            'durable-objects': 'Durable Objects',
            'email-routing': 'Email Routing',
            'google-tag-gateway': 'Google Tag Gateway',
            'hyperdrive': 'Hyperdrive',
            'images': 'Images',
            'kv': 'KV',
            'pages': 'Pages',
            'pipelines': 'Pipelines',
            'queues': 'Queues',
            'r2': 'R2',
            'r2-sql': 'R2 SQL',
            'realtime': 'Realtime',
            'sandbox': 'Sandbox',
            'secrets-store': 'Secrets Store',
            'stream': 'Stream',
            'vectorize': 'Vectorize',
            'web3': 'Web3',
            'workers': 'Workers',
            'workers-ai': 'Workers AI',
            'workers-vpc': 'Workers VPC',
            'workflows': 'Workflows',
            'zaraz': 'Zaraz',
        }
    },
}

# Common products that appear in all category queries
COMMON_PRODUCTS = {
    'support': 'Support',
    'fundamentals': 'Fundamentals',
    'terraform': 'Terraform',
}

# Mapping from changelog directory names to doc directory names
# (only for directories that differ between changelog and docs)
CHANGELOG_TO_DOCS_MAP = {
    'access': 'cloudflare-one',
    'audit-logs': 'fundamentals',
    'browser-isolation': 'cloudflare-one',
    'casb': 'cloudflare-one',
    'cloudflare-tunnel': 'cloudflare-one',
    'dex': 'cloudflare-one',
    'dlp': 'cloudflare-one',
    'email-security-cf1': 'cloudflare-one',
    'gateway': 'cloudflare-one',
    'risk-score': 'cloudflare-one',
    'sdk': 'terraform',
    'workers-for-platforms': 'cloudflare-for-platforms',
    'zero-trust-warp': 'warp-client',
}


def get_tracked_products(categories=None):
    """Get products to track based on selected categories.
    
    Args:
        categories: List of category keys (e.g., ['app_perf', 'app_sec']).
                   If None, returns all products from all categories.
    
    Returns:
        Dictionary mapping product directory to display name.
    """
    products = dict(COMMON_PRODUCTS)  # Always include common products
    
    if categories is None:
        # Include all categories
        for cat_data in CATEGORIES.values():
            products.update(cat_data['products'])
    else:
        # Include only specified categories
        for cat_key in categories:
            if cat_key in CATEGORIES:
                products.update(CATEGORIES[cat_key]['products'])
    
    return products

# Patterns to identify trivial changes (exclude these)
TRIVIAL_PATTERNS = [
    r'\btypo\b',
    r'\bfix typo\b',
    r'\bformatting\b',
    r'\bwhitespace\b',
    r'\bminor\b',
    r'\bupdate link\b',
    r'\bbroken link\b',
    r'\bfix link\b',
    r'\bstyle\b',
    r'\bindentation\b',
    r'\bpunctuation\b',
    r'\bspelling\b',
    r'\bdash button\b',
    r'\bdashbutton\b',
]

# Patterns to identify significant changes (prioritize these)
SIGNIFICANT_PATTERNS = [
    r'\bnew feature\b',
    r'\badd\b.*\bsection\b',
    r'\bnew\b.*\bguide\b',
    r'\bupdate\b.*\bapi\b',
    r'\bdeprecate\b',
    r'\bannounce\b',
    r'\brelease\b',
    r'\bmajor\b',
]

BASE_URL = 'https://developers.cloudflare.com'

# Global variable to store repository path
REPO_PATH = None


def run_git_command(cmd):
    """Execute a git command and return output."""
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, cwd=REPO_PATH)
    return result.stdout.strip()


def get_changelog_commits_in_range(start_date, end_date):
    """Get commits for changelog directory within date range."""
    date_filter = f"--since='{start_date}' --until='{end_date}'"
    path_filter = '-- src/content/changelog/'
    
    cmd = f"git log {date_filter} --date-order --pretty=format:'%H|%s|%ci|%cn' {path_filter}"
    output = run_git_command(cmd)
    
    if not output:
        return []
    
    commits = []
    for line in output.split('\n'):
        if line:
            parts = line.split('|', 3)
            if len(parts) >= 4:
                hash_val, subject, date, author = parts
                commits.append({
                    'hash': hash_val,
                    'subject': subject,
                    'date': date,
                    'author': author
                })
    
    return commits


def get_commits_in_range(start_date, end_date, product_paths):
    """Get commits for specified product paths within date range."""
    date_filter = f"--since='{start_date}' --until='{end_date}'"
    path_filter = ' '.join([f'-- src/content/docs/{path}/' for path in product_paths])
    
    # Use committer date (merge date) instead of author date
    cmd = f"git log {date_filter} --date-order --pretty=format:'%H|%s|%ci|%cn' {path_filter}"
    output = run_git_command(cmd)
    
    if not output:
        return []
    
    commits = []
    for line in output.split('\n'):
        if line:
            hash_val, subject, date, author = line.split('|', 3)
            commits.append({
                'hash': hash_val,
                'subject': subject,
                'date': date,
                'author': author
            })
    
    return commits


def get_changed_files(commit_hash):
    """Get list of changed files for a commit."""
    cmd = f"git diff-tree --no-commit-id --name-only -r {commit_hash}"
    output = run_git_command(cmd)
    return [f for f in output.split('\n') if f]


def clean_commit_subject(subject):
    """Remove PR numbers and other noise from commit subject."""
    # Remove PR numbers like (#12345)
    subject = re.sub(r'\s*\(#\d+\)\s*$', '', subject)
    return subject.strip()


def is_trivial_change(commit_subject):
    """Check if commit is a trivial change."""
    subject_lower = commit_subject.lower()
    return any(re.search(pattern, subject_lower, re.IGNORECASE) for pattern in TRIVIAL_PATTERNS)


def is_significant_change(commit_subject):
    """Check if commit is a significant change."""
    subject_lower = commit_subject.lower()
    return any(re.search(pattern, subject_lower, re.IGNORECASE) for pattern in SIGNIFICANT_PATTERNS)


def extract_product_from_path(file_path, tracked_products):
    """Extract product name from file path."""
    match = re.match(r'src/content/docs/([^/]+)/', file_path)
    if match:
        product_dir = match.group(1)
        return tracked_products.get(product_dir, None)
    return None


def extract_changelog_product(file_path, tracked_products):
    """Extract product name from changelog file path, mapping to doc categories."""
    match = re.match(r'src/content/changelog/([^/]+)/', file_path)
    if match:
        changelog_dir = match.group(1)
        # Map changelog directory to docs directory if different
        docs_dir = CHANGELOG_TO_DOCS_MAP.get(changelog_dir, changelog_dir)
        return tracked_products.get(docs_dir, None)
    return None


def parse_changelog_frontmatter(file_path):
    """Parse frontmatter from a changelog file to extract title and date."""
    full_path = os.path.join(REPO_PATH, file_path)
    if not os.path.exists(full_path):
        return None, None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # Read first 2000 chars (enough for frontmatter)
    except Exception:
        return None, None
    
    title = None
    date = None
    in_frontmatter = False
    
    for line in content.split('\n'):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter:
            if line.startswith('title:'):
                title = line.replace('title:', '').strip()
                # Remove quotes if present
                if title.startswith('"') and title.endswith('"'):
                    title = title[1:-1]
                elif title.startswith("'") and title.endswith("'"):
                    title = title[1:-1]
            elif line.startswith('date:'):
                date = line.replace('date:', '').strip()
    
    return title, date


def get_changelog_entries_in_date_range(start_date, end_date, tracked_products):
    """Scan changelog directory and return entries within the date range based on frontmatter date."""
    changelog_dir = os.path.join(REPO_PATH, 'src/content/changelog')
    if not os.path.isdir(changelog_dir):
        return {}
    
    changelog_by_product = defaultdict(list)
    
    # Walk through all changelog subdirectories
    for product_dir in os.listdir(changelog_dir):
        product_path = os.path.join(changelog_dir, product_dir)
        if not os.path.isdir(product_path):
            continue
        
        # Map changelog directory to docs directory
        docs_dir = CHANGELOG_TO_DOCS_MAP.get(product_dir, product_dir)
        product_name = tracked_products.get(docs_dir)
        
        if not product_name:
            continue
        
        # Scan all .mdx files in this product's changelog directory
        for filename in os.listdir(product_path):
            if not filename.endswith('.mdx'):
                continue
            
            file_path = f'src/content/changelog/{product_dir}/{filename}'
            title, entry_date = parse_changelog_frontmatter(file_path)
            
            if not entry_date:
                continue
            
            # Check if entry date is within the range
            if start_date <= entry_date <= end_date:
                url = changelog_file_to_url(file_path)
                changelog_by_product[product_name].append({
                    'title': title or filename,
                    'url': url,
                    'date': entry_date,
                    'file': file_path
                })
    
    # Sort entries by date within each product
    for product in changelog_by_product:
        changelog_by_product[product].sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return changelog_by_product


def changelog_file_to_url(file_path):
    """Convert changelog file path to documentation URL."""
    if not file_path.startswith('src/content/changelog/'):
        return None
    
    # Extract just the filename (without category directory)
    # e.g., src/content/changelog/fundamentals/2026-01-19-http3-499-reporting-improvement.mdx
    # becomes: changelog/2026-01-19-http3-499-reporting-improvement/
    match = re.match(r'src/content/changelog/[^/]+/(.+)\.mdx?$', file_path)
    if match:
        filename = match.group(1).lower()  # Lowercase for URL
        filename = filename.replace('.', '')  # Remove dots (site sanitizes them)
        return f"{BASE_URL}/changelog/{filename}/"
    
    return None


def file_to_url(file_path):
    """Convert file path to documentation URL."""
    if not file_path.startswith('src/content/docs/'):
        return None
    
    # Remove src/content/docs/ prefix and file extension
    path = file_path.replace('src/content/docs/', '')
    path = re.sub(r'\.(mdx?|html)$', '', path)
    
    # Handle index files
    if path.endswith('/index'):
        path = path[:-6]
    
    return f"{BASE_URL}/{path}/"


def get_file_sections(commit_hash, file_path):
    """Extract section headers that were added/modified in a commit."""
    cmd = f"git show {commit_hash} -- {file_path} | grep '^[+-]##' | head -5"
    output = run_git_command(cmd)
    
    sections = []
    for line in output.split('\n'):
        if line.startswith(('+##', '-##')):
            # Extract section title
            section = re.sub(r'^[+-]##\s*', '', line).strip()
            if section and not section.startswith('#'):
                sections.append(section)
    
    return list(set(sections))[:3]  # Return up to 3 unique sections


def generate_summary(commits_by_product, month_name):
    """Generate formatted summary of changes."""
    output = []
    output.append(f"# Documentation Updates - {month_name}\n")
    
    for product, commits in sorted(commits_by_product.items()):
        if not commits:
            continue
        
        for commit in commits:
            # Get changed files
            files = get_changed_files(commit['hash'])
            doc_files = [f for f in files if f.startswith('src/content/docs/')]
            
            if not doc_files:
                continue
            
            # Generate summary line with product category
            clean_subject = clean_commit_subject(commit['subject'])
            output.append(f"\nUpdate to the {product} documentation: {clean_subject}")
            
            # Add file links
            for file_path in doc_files[:3]:  # Limit to 3 files per commit
                url = file_to_url(file_path)
                if url:
                    sections = get_file_sections(commit['hash'], file_path)
                    if sections:
                        output.append(f"   - {url} - Updated: {', '.join(sections)}")
                    else:
                        output.append(f"   - {url}")
            
            if len(doc_files) > 3:
                output.append(f"   - ... and {len(doc_files) - 3} more files")
    
    return '\n'.join(output)


def generate_changelog_summary(changelog_by_product, month_name):
    """Generate formatted summary of new changelog entries."""
    output = []
    output.append(f"\n\n# New Changelog Entries - {month_name}\n")
    
    has_entries = False
    for product, entries in sorted(changelog_by_product.items()):
        if not entries:
            continue
        
        has_entries = True
        for entry in entries:
            title = entry.get('title', 'Untitled')
            url = entry.get('url', '')
            output.append(f"\nNew changelog entry for {product}: {title}")
            if url:
                output.append(f"   - {url}")
    
    if not has_entries:
        output.append("\nNo new changelog entries found for tracked products.")
    
    return '\n'.join(output)


def main():
    global REPO_PATH
    
    parser = argparse.ArgumentParser(description='Track documentation changes')
    parser.add_argument('--repo', type=str, required=True,
                        help='Path to cloudflare-docs repository')
    parser.add_argument('--month', type=str, help='Month in YYYY-MM format (default: last month)')
    parser.add_argument('--category', type=str, nargs='+',
                        choices=['app_perf', 'app_sec', 'cf1', 'platform', 'dev_plat'],
                        help='Category to track: app_perf (Application Performance), '
                             'app_sec (Application Security), cf1 (Cloudflare One), '
                             'platform (Platform), dev_plat (Developer Platform). '
                             'Default: all categories')
    parser.add_argument('--products', type=str, nargs='+', help='Specific products to track (overrides --category)')
    parser.add_argument('--include-trivial', action='store_true', help='Include trivial changes')
    parser.add_argument('--output', type=str, help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Set repository path
    REPO_PATH = os.path.expanduser(args.repo)
    
    # Validate repository path
    if not os.path.isdir(REPO_PATH):
        print(f"Error: Repository path does not exist: {REPO_PATH}")
        return 1
    
    git_dir = os.path.join(REPO_PATH, '.git')
    if not os.path.isdir(git_dir):
        print(f"Error: Not a git repository: {REPO_PATH}")
        return 1
    
    # Determine date range
    if args.month:
        start_date = datetime.strptime(args.month, '%Y-%m')
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        # Default to last month
        today = datetime.now()
        end_date = today.replace(day=1) - timedelta(days=1)
        start_date = end_date.replace(day=1)
    
    month_name = start_date.strftime('%B %Y')
    
    # Determine products to track
    if args.products:
        # Specific products override category selection
        tracked_products = get_tracked_products()  # Get all to validate
        products_to_track = args.products
        # Filter tracked_products to only include specified products
        tracked_products = {k: v for k, v in tracked_products.items() if k in products_to_track}
    else:
        # Use category selection (or all if not specified)
        tracked_products = get_tracked_products(args.category)
        products_to_track = list(tracked_products.keys())
    
    # Display category info
    if args.category:
        cat_names = [CATEGORIES[c]['name'] for c in args.category]
        print(f"Categories: {', '.join(cat_names)}")
    
    print(f"Repository: {REPO_PATH}")
    print(f"Tracking changes for {month_name}...")
    print(f"Products: {', '.join(products_to_track)}")
    
    # Get commits for docs
    commits = get_commits_in_range(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        products_to_track
    )
    
    print(f"Found {len(commits)} doc commits")
    
    # Filter and organize commits
    commits_by_product = defaultdict(list)
    
    for commit in commits:
        # Skip trivial changes unless explicitly included
        if not args.include_trivial and is_trivial_change(commit['subject']):
            continue
        
        # Get changed files to determine product
        files = get_changed_files(commit['hash'])
        for file_path in files:
            product = extract_product_from_path(file_path, tracked_products)
            if product and commit not in commits_by_product[product]:
                commits_by_product[product].append(commit)
    
    # Get changelog entries based on frontmatter date (not commit date)
    changelog_by_product = get_changelog_entries_in_date_range(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        tracked_products
    )
    
    total_changelog_entries = sum(len(entries) for entries in changelog_by_product.values())
    print(f"Found {total_changelog_entries} changelog entries")
    
    # Generate summaries
    summary = generate_summary(commits_by_product, month_name)
    changelog_summary = generate_changelog_summary(changelog_by_product, month_name)
    
    full_output = summary + changelog_summary
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(full_output)
        print(f"\nSummary written to {args.output}")
    else:
        print("\n" + "="*80)
        print(full_output)
    
    return 0


if __name__ == '__main__':
    exit(main())
