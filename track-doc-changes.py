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

# Product areas to track (Application Performance related)
TRACKED_PRODUCTS = {
    'cache': 'Cache',
    'speed': 'Speed',
    'load-balancing': 'Load Balancing',
    'automatic-platform-optimization': 'Automatic Platform Optimization',
    'ssl': 'SSL/TLS',
    'dns': 'DNS',
    'spectrum': 'Spectrum',
    'health-checks': 'Health Checks',
    'support': 'Support',
    'logs': 'Logs',
    'analytics': 'Analytics',
    'cloudflare-for-platforms': 'Cloudflare for SaaS',
    'notifications': 'Notifications',
    'rules': 'Rules',
    'smart-shield': 'Smart Shield',
    'terraform': 'Terraform',
    'version-management': 'Version Management',
}

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


def extract_product_from_path(file_path):
    """Extract product name from file path."""
    match = re.match(r'src/content/docs/([^/]+)/', file_path)
    if match:
        product_dir = match.group(1)
        return TRACKED_PRODUCTS.get(product_dir, product_dir)
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


def main():
    global REPO_PATH
    
    parser = argparse.ArgumentParser(description='Track documentation changes')
    parser.add_argument('--repo', type=str, required=True,
                        help='Path to cloudflare-docs repository')
    parser.add_argument('--month', type=str, help='Month in YYYY-MM format (default: last month)')
    parser.add_argument('--products', type=str, nargs='+', help='Specific products to track')
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
    products_to_track = args.products if args.products else list(TRACKED_PRODUCTS.keys())
    
    print(f"Repository: {REPO_PATH}")
    print(f"Tracking changes for {month_name}...")
    print(f"Products: {', '.join(products_to_track)}")
    
    # Get commits
    commits = get_commits_in_range(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        products_to_track
    )
    
    print(f"Found {len(commits)} commits")
    
    # Filter and organize commits
    commits_by_product = defaultdict(list)
    
    for commit in commits:
        # Skip trivial changes unless explicitly included
        if not args.include_trivial and is_trivial_change(commit['subject']):
            continue
        
        # Get changed files to determine product
        files = get_changed_files(commit['hash'])
        for file_path in files:
            product = extract_product_from_path(file_path)
            if product and commit not in commits_by_product[product]:
                commits_by_product[product].append(commit)
    
    # Generate summary
    summary = generate_summary(commits_by_product, month_name)
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(summary)
        print(f"\nSummary written to {args.output}")
    else:
        print("\n" + "="*80)
        print(summary)
    
    return 0


if __name__ == '__main__':
    exit(main())
