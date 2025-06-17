# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit-based ticket analytics dashboard for BUMA (Business Unit Management Analytics). The application analyzes IT service desk tickets and provides SLA compliance reporting through interactive visualizations.

## Key Architecture

- **Main Application**: `app.py` - Single-file Streamlit dashboard
- **Data Model**: Star schema with fact table (FactTicketsCleaned.csv) and dimension tables (DimDate, DimPriority, DimService, DimChannel)
- **Key Metrics**: Ticket volumes vs baseline, SLA compliance by priority, service performance analysis
- **Visualization**: Plotly Express charts embedded in Streamlit interface

## Data Structure

The fact table contains ticket records with these key fields:
- `Number`: Ticket ID (e.g., INC16102665)
- `OpenedDatetime`/`ResolvedDatetime`: Ticket lifecycle timestamps
- `ResolutionMinutes`: Time to resolve
- `PriorityShort`: Priority level (P1-P4)
- `Tower`: Service tower/team
- `Channel`: Request channel (Email, etc.)
- `Service`: Specific service affected

## Common Commands

### Environment Setup
```bash
# Install dependencies using the provided script
./install_requirements.sh requirements.txt venv
# OR manually with pip
pip install -r requirements.txt
```

### Running the Application
```bash
streamlit run app.py
```

## Development Notes

- The dashboard expects all CSV files to be present in the root directory
- Missing `SLA_Met` column in FactTicketsCleaned.csv causes some features to be commented out (lines 37-38)
- Charts use log scale for resolution time distributions due to wide variance
- Top 10 filtering applied to tower analysis for readability
- Data quality checks included for unassigned closed tickets