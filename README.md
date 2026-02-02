# Cloudflare Docs Change Tracker

A Python script to automatically track and summarize documentation changes in the Cloudflare documentation repository. This tool analyzes git commit history to generate monthly reports of documentation updates for specific product areas.

## Purpose

This script helps documentation maintainers:
- Track changes to specific product documentation areas
- Generate monthly summaries of documentation updates
- Filter out trivial changes (typos, formatting, etc.)
- Identify which pages were updated and what sections changed
- Create reports suitable for sharing with stakeholders

## Features

- **Date-based filtering**: Track changes by month using merge dates
- **Product-specific tracking**: Focus on specific product areas (Cache, DNS, SSL/TLS, etc.)
- **Smart filtering**: Automatically excludes trivial changes like typos and formatting
- **Section detection**: Identifies which sections of a page were modified
- **Clean output**: Generates formatted summaries ready for copy-paste into Confluence or other tools

## Requirements

- Python 3.6+
- Git
- Access to a local clone of the cloudflare-docs repository

## Installation

1. Download the script:
```bash
curl -O https://raw.githubusercontent.com/ngayerie/spm-doc-updates-tracker/main/track-doc-changes.py
chmod +x track-doc-changes.py
```

2. Clone the Cloudflare docs repository (if you haven't already):
```bash
git clone https://github.com/cloudflare/cloudflare-docs.git
```

## Usage

### Basic Usage

Track changes for the last month:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs
```

### Specify a Month

Track changes for a specific month:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs --month 2024-12
```

### Track by Category

Focus on a specific category:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs --month 2024-12 --category app_perf
```

Track multiple categories:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs --month 2024-12 --category app_perf app_sec
```

### Track Specific Products

Override categories and focus on specific products:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs --month 2024-12 --products cache dns ssl
```

### Save Output to File

Generate a report file:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs --month 2024-12 --output december-updates.txt
```

### Include Trivial Changes

By default, trivial changes (typos, formatting) are excluded. To include them:
```bash
python3 track-doc-changes.py --repo /path/to/cloudflare-docs --month 2024-12 --include-trivial
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--repo` | Yes | Path to the cloudflare-docs repository |
| `--month` | No | Month in YYYY-MM format (default: last month) |
| `--category` | No | Category to track: `app_perf`, `app_sec`, `cf1`, `platform`, `dev_plat` (default: all) |
| `--products` | No | Specific products to track (overrides `--category`) |
| `--include-trivial` | No | Include trivial changes like typos and formatting |
| `--output` | No | Output file path (default: stdout) |

## Categories

The script organizes products into 5 categories:

### Application Performance (`app_perf`)
Argo Smart Routing, Automatic Platform Optimization, Cache, Cloudflare for SaaS, Data Localization, DNS, Health Checks, Load Balancing, Logs, Rules, Speed, SSL/TLS, Version Management, 1.1.1.1

### Application Security (`app_sec`)
API Shield, Bot Management, Cloudflare Challenges, DDoS Protection, Firewall, Log Explorer, Page Shield, Ruleset Engine, Security, Security Center, Smart Shield, Turnstile, WAF, Waiting Room

### Cloudflare One (`cf1`)
Browser Rendering, BYOIP, China Network, Client IP Geolocation, Cloudflare One, Email Security, Magic Cloud Networking, Magic Firewall, Magic Network Monitoring, Magic Transit, Magic WAN, Network, Network Error Logging, Network Interconnect, Spectrum, WARP Client

### Platform (`platform`)
Analytics, Billing, Notifications, Pulumi, Radar, Registrar, Tenant, Time Services

### Developer Platform (`dev_plat`)
Agents, AI Crawl Control, AI Gateway, AI Search, Containers, D1, DMARC Management, Durable Objects, Email Routing, Google Tag Gateway, Hyperdrive, Images, KV, Pages, Pipelines, Queues, R2, R2 SQL, Realtime, Sandbox, Secrets Store, Stream, Vectorize, Web3, Workers, Workers AI, Workers VPC, Workflows, Zaraz

### Always Included
The following products are always included regardless of category selection:
- Support
- Fundamentals
- Terraform

## Output Format

The script generates output in the following format:

```
# Documentation Updates - December 2024

Update to the Cache documentation: Add new caching strategies guide
   - https://developers.cloudflare.com/cache/strategies/

Update to the DNS documentation: Update DNSSEC configuration steps
   - https://developers.cloudflare.com/dns/dnssec/ - Updated: Configuration, Troubleshooting
```

## Customization

You can customize the script by editing:

1. **CATEGORIES**: Add or remove products within categories
2. **TRIVIAL_PATTERNS**: Adjust what counts as trivial changes
3. **SIGNIFICANT_PATTERNS**: Define patterns for significant changes

## Examples

### Example 1: Monthly Report for Application Performance Category

```bash
python3 track-doc-changes.py \
  --repo ~/cloudflare-docs \
  --month 2024-12 \
  --category app_perf \
  --output december-app-performance.txt
```

### Example 2: Track Multiple Categories

```bash
python3 track-doc-changes.py \
  --repo ~/cloudflare-docs \
  --month 2024-12 \
  --category app_sec cf1 \
  --output december-security-network.txt
```

### Example 3: All Changes Including Trivial Ones

```bash
python3 track-doc-changes.py \
  --repo ~/cloudflare-docs \
  --month 2024-12 \
  --include-trivial \
  --output december-all-changes.txt
```

### Example 4: Quick Check of Last Month

```bash
python3 track-doc-changes.py --repo ~/cloudflare-docs
```

## Workflow Tips

1. **Keep your local repository updated**:
   ```bash
   cd /path/to/cloudflare-docs
   git checkout production
   git pull origin production
   ```

2. **Run the script monthly** to generate regular reports

3. **Copy output to Confluence** or your documentation tracking system

4. **Adjust filters** based on your team's needs

## Troubleshooting

**Error: Repository path does not exist**
- Ensure the path to your cloudflare-docs repository is correct
- Use absolute paths or `~` for home directory

**Error: Not a git repository**
- Make sure you're pointing to a valid git repository
- Check that the `.git` directory exists

**No commits found**
- Verify the date range includes commits
- Check that the product paths are correct
- Ensure your local repository is up to date

## Contributing

Feel free to submit issues or pull requests to improve this tool.

## License

MIT License - feel free to use and modify as needed.
