#!/bin/bash
# Build script for Vercel deployment

echo "Starting build process for Jail Roster Scraper demo..."

# Install dependencies
echo "Installing dependencies..."
pip install -r dashboard/requirements.txt
pip install -r scraper/requirements.txt

# Generate demo data
echo "Generating demo data..."
python api/generate_demo_data.py

echo "Build process complete!"