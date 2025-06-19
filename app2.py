import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import os

# --- Page Configuration ------------------------------------------------
st.set_page_config(page_title="BUMA Ticket Dashboard",
                   layout="wide",
                   initial_sidebar_state="collapsed")

# --- Custom CSS to make the app wider and position popovers ---------
st.markdown("""
<style>
    .stVerticalBlock {
        max-width: 95% !important;
        width: 95% !important;
    }
    .stMainBlockContainer {
        max-width: 95% !important;
        width: 95% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    .main > div {
        max-width: 95% !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Position popover buttons closer to headings */
    .stPopover > button {
        margin-left: -20px !important;
        margin-top: 5px !important;
        background-color: transparent !important;
        border: 1px solid #ccc !important;
        border-radius: 50% !important;
        width: 24px !important;
        height: 24px !important;
        padding: 0 !important;
        font-size: 14px !important;
    }
    
    /* Reduce spacing between headings and popovers */
    .stMarkdown + .stPopover {
        margin-top: -40px !important;
        margin-left: 10px !important;
    }
    
    /* For popovers in columns */
    div[data-testid="column"] .stPopover {
        margin-top: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Constants for DataFrame Columns -----------------------------------
COL_OPENED = "Opened"
COL_RESOLVED = "Resolved"
COL_YEAR_MONTH = "YearMonth"
COL_PRIORITY = "Priority"
COL_PRIORITY_NUMERIC = "Priority_Numeric"
COL_RESOLUTION_DAYS = "Resolution_Days"
COL_SLA_TARGET_HOURS = "SLA_Target_Hours"
COL_RESOLUTION_HOURS = "Resolution_Hours"
COL_SLA_MET = "SLA_Met"
COL_NUMBER = "Number"
COL_STATE = "State"
COL_ASSIGNMENT_GROUP = "Assignment group"
COL_CHANNEL = "Channel"
COL_LOCATION = "Location"
COL_CATEGORIZATION = "Categorization"
COL_ASSIGNED_TO = "Assigned to"
COL_CONFIG_ITEM = "Configuration item"
COL_SHORT_DESC = "Short description"

# --- TCD.CSV Enhanced Columns ------------------------------------------
COL_REFERENCE = "Reference"
COL_GROUP = "Group"
COL_TOWER = "Tower"
COL_SERVICE_REQUEST = "Service Request"
COL_SR_RESULT = "SR Result"
COL_TASK_TYPE = "Task Type"
COL_ENHANCEMENT = "Enhancement"
COL_ENH_RESULT = "ENH Result"

# --- Filename Constant -------------------------------------------------
DEFAULT_CSV_FILE = "tcd.csv"

# --- State Constants ---------------------------------------------------
STATE_ACTIVE = "Active"
STATE_WIP = "Work In Progress"
STATE_AWAITING_USER = "Awaiting User Info"
STATE_NEW = "New"
STATE_CLOSED = "Closed"
STATE_RESOLVED = "Resolved"
STATE_CANCELLED = "Cancelled"

OPEN_STATES = [STATE_ACTIVE, STATE_WIP, STATE_AWAITING_USER, STATE_NEW]
CLOSED_STATES = [STATE_CLOSED, STATE_RESOLVED, STATE_CANCELLED]


# --- Helper Functions -------------------------------------------------
def st_header_with_popover(header, popover_text):
    """Renders a markdown header with a popover question mark icon."""
    st.markdown(f"### {header}")
    with st.popover("❓"):
        st.markdown(popover_text)

def st_subheader_with_popover(header, popover_text):
    """Renders a subheader with a popover, designed for use in columns."""
    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write(f"#### {header}")
    with col2:
        with st.popover("❓"):
            st.markdown(popover_text)

# --- Load data ------------------------------------------------------
@st.cache_data
def load_data(file):
    # Try different encodings to handle various file formats
    try:
        df = pd.read_csv(file, parse_dates=[COL_OPENED, COL_RESOLVED], encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(file, parse_dates=[COL_OPENED, COL_RESOLVED], encoding="latin-1")
    
    # Clean and process data
    df[COL_YEAR_MONTH] = df[COL_OPENED].dt.to_period("M").astype(str)
    df[COL_PRIORITY_NUMERIC] = df[COL_PRIORITY].str.extract(r'(\d+)').astype(int)
    df[COL_RESOLUTION_DAYS] = (df[COL_RESOLVED] - df[COL_OPENED]).dt.total_seconds() / (24 * 3600)
    
    # BUMA Contract SLA Requirements - Resolution Targets
    # P1: 4 hours, P2: 8 hours, P3: 5 business days (40h), P4: 20 business days (160h)
    df[COL_SLA_TARGET_HOURS] = df[COL_PRIORITY_NUMERIC].map({1: 4, 2: 8, 3: 40, 4: 160})
    df[COL_RESOLUTION_HOURS] = df[COL_RESOLUTION_DAYS] * 24
    df[COL_SLA_MET] = df[COL_RESOLUTION_HOURS] <= df[COL_SLA_TARGET_HOURS]
    
    # BUMA Contract SLA - Response Time Requirements 
    # P1/P2: 30 minutes, P3/P4: 1 business day (8 hours)
    df["Response_Target_Hours"] = df[COL_PRIORITY_NUMERIC].map({1: 0.5, 2: 0.5, 3: 8, 4: 8})
    # Note: Response time would need 'First Response' timestamp in real data
    # For now, using placeholder values
    df["Response_Hours"] = 0  # Placeholder - needs actual response timestamp
    df["Response_SLA_Met"] = True  # Placeholder - needs actual calculation
    
    # BUMA Contract Financial Impact - Credit Percentages
    df["Resolution_Credit_Pct"] = df[COL_PRIORITY_NUMERIC].map({1: 18, 2: 12, 3: 10, 4: 6})
    df["Response_Credit_Pct"] = df[COL_PRIORITY_NUMERIC].map({1: 8, 2: 5, 3: 4, 4: 3})
    
    # SLA Performance Levels (Expected: 95%, Minimum: 90%)
    df["Expected_SLA_Target"] = 0.95
    df["Minimum_SLA_Target"] = 0.90
    
    return df

def render_overview_tab(filtered_df):
    """Renders the content for the Overview tab."""
    st_header_with_popover(
        "Monthly Ticket Trends",
        """
        **Purpose**: Track ticket volume patterns over time to identify seasonal trends, capacity planning needs, and workload fluctuations.
        
        **Key Insights**: 
        - Seasonal patterns in ticket creation
        - Growth or decline trends
        - Capacity planning indicators
        
        **Graph Explanation**: Line chart with markers showing ticket count per month. Upward trends indicate increasing workload, downward trends show improvement or seasonal effects.
        """
    )
    monthly_tickets = filtered_df.groupby(COL_YEAR_MONTH).size().reset_index(name="Tickets")
    monthly_tickets = monthly_tickets.sort_values(COL_YEAR_MONTH)
    
    fig1 = px.line(monthly_tickets, x=COL_YEAR_MONTH, y="Tickets",
                   markers=True, 
                   title="Monthly Ticket Volume Trend",
                   labels={"Tickets": "Number of Tickets", COL_YEAR_MONTH: "Month"})
    fig1.update_xaxes(tickangle=45)
    st.plotly_chart(fig1, use_container_width=True)
    
    # Monthly Trends Insights
    if len(monthly_tickets) > 1:
        st.write("#### Monthly Volume Insights")
        
        latest_month = monthly_tickets.iloc[-1]
        previous_month = monthly_tickets.iloc[-2] if len(monthly_tickets) > 1 else None
        
        col1, col2 = st.columns(2)
        with col1:
            if previous_month is not None:
                current_tickets = latest_month['Tickets']
                previous_tickets = previous_month['Tickets']
                current_month_name = latest_month[COL_YEAR_MONTH]
                previous_month_name = previous_month[COL_YEAR_MONTH]
                
                # Always show actual numbers with percentage when meaningful
                if previous_tickets >= 1:  # Calculate percentage for any baseline
                    month_change = ((current_tickets - previous_tickets) / previous_tickets * 100)
                    
                    if month_change > 300:
                        st.warning(f"📈 **Major Spike**: {current_tickets} vs {previous_tickets} tickets (>300% increase) - {current_month_name} vs {previous_month_name}")
                    elif month_change > 25:
                        st.warning(f"📈 **Volume Spike**: {current_tickets} vs {previous_tickets} tickets (+{month_change:.1f}%) - {current_month_name} vs {previous_month_name}")
                    elif month_change < -25:
                        st.success(f"📉 **Volume Drop**: {current_tickets} vs {previous_tickets} tickets ({month_change:.1f}%) - {current_month_name} vs {previous_month_name}")
                    else:
                        st.info(f"📊 **Month Change**: {current_tickets} vs {previous_tickets} tickets ({month_change:.1f}%) - {current_month_name} vs {previous_month_name}")
                else:
                    # Show raw numbers when percentage isn't meaningful
                    change_abs = current_tickets - previous_tickets
                    if change_abs > 0:
                        st.info(f"📈 **Month Change**: {current_tickets} vs {previous_tickets} tickets (+{change_abs}) - {current_month_name} vs {previous_month_name}")
                    elif change_abs < 0:
                        st.info(f"📉 **Month Change**: {current_tickets} vs {previous_tickets} tickets ({change_abs}) - {current_month_name} vs {previous_month_name}")
                    else:
                        st.info(f"📊 **Month Change**: {current_tickets} tickets (unchanged) - {current_month_name}")
            else:
                # When only one month available, show that month's data
                current_tickets = latest_month['Tickets']
                current_month_name = latest_month[COL_YEAR_MONTH]
                st.info(f"📊 **Single Month**: {current_tickets} tickets ({current_month_name}) - need previous month for comparison")
        
        with col2:
            # Calculate quarterly trend using recent vs previous quarters
            if len(monthly_tickets) >= 6:
                # Compare most recent 3 months vs previous 3 months (not first 3 months)
                recent_3_months = monthly_tickets.tail(3)['Tickets'].mean()
                previous_3_months = monthly_tickets.iloc[-6:-3]['Tickets'].mean()  # 3 months before the recent 3
                
                if previous_3_months > 0:
                    trend_change = ((recent_3_months - previous_3_months) / previous_3_months * 100)
                    
                    # Get month names for context
                    recent_period = f"{monthly_tickets.iloc[-3]['YearMonth']} to {monthly_tickets.iloc[-1]['YearMonth']}"
                    previous_period = f"{monthly_tickets.iloc[-6]['YearMonth']} to {monthly_tickets.iloc[-4]['YearMonth']}"
                    
                    # Show quarterly comparison with context
                    if trend_change > 50:
                        st.warning(f"📈 **Quarterly Growth**: {recent_3_months:.0f} vs {previous_3_months:.0f} tickets/month avg (+{trend_change:.1f}%) - {recent_period} vs {previous_period}")
                    elif trend_change > 15:
                        st.info(f"📈 **Quarterly Trend**: {recent_3_months:.0f} vs {previous_3_months:.0f} tickets/month avg (+{trend_change:.1f}%) - {recent_period} vs {previous_period}")
                    elif trend_change < -15:
                        st.success(f"📉 **Quarterly Decline**: {recent_3_months:.0f} vs {previous_3_months:.0f} tickets/month avg ({trend_change:.1f}%) - {recent_period} vs {previous_period}")
                    else:
                        st.info(f"📊 **Quarterly Stable**: {recent_3_months:.0f} vs {previous_3_months:.0f} tickets/month avg ({trend_change:.1f}%) - {recent_period} vs {previous_period}")
                else:
                    st.info(f"📊 **Recent Quarter**: {recent_3_months:.0f} tickets/month avg ({recent_period})")
            elif len(monthly_tickets) >= 3:
                # For 3-5 months, just show recent average with period
                recent_avg = monthly_tickets.tail(3)['Tickets'].mean()
                period = f"{monthly_tickets.iloc[-3]['YearMonth']} to {monthly_tickets.iloc[-1]['YearMonth']}"
                st.info(f"📊 **Recent Quarter**: {recent_avg:.0f} tickets/month avg ({period})")
            else:
                st.info("📊 **Trend Analysis**: Need at least 3 months of data")

    # Service Category Risk Management
    st_header_with_popover(
        "Service Category Risk Analysis",
        """
        **Purpose**: Monitor service categories based on actual ticket priority levels (P1-P4) for proactive risk management.
        
        **Analysis Approach**:
        - **Priority-Based Assessment**: Uses actual P1/P2 incident counts instead of arbitrary criticality
        - **High Priority Rate**: Percentage of P1/P2 incidents per category
        - **Risk Scoring**: Combines volume, SLA performance, and high-priority incident rate
        - **Data-Driven Insights**: Based on real ticket priority classifications
        
        **Key Metrics**:
        - **P1 Incidents**: Highest priority, immediate business impact
        - **P2 Incidents**: High priority, significant business impact  
        - **High Priority Rate**: (P1 + P2) / Total tickets percentage
        - **SLA Compliance**: Resolution performance vs contract targets
        - **Volume Impact**: Total ticket count for resource planning
        
        **Benefits**: Objective risk assessment using established ITIL priority levels
        """
    )
    
    # Calculate service category risk metrics
    if COL_CATEGORIZATION in filtered_df.columns:
        category_risk = (
            filtered_df.groupby(COL_CATEGORIZATION)
            .agg(
                Tickets=(COL_NUMBER, "count"),
                Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
                SLA_Compliance=(COL_SLA_MET, "mean"),
                P1_Incidents=(COL_PRIORITY_NUMERIC, lambda x: (x == 1).sum()),
                P2_Incidents=(COL_PRIORITY_NUMERIC, lambda x: (x == 2).sum())
            )
            .reset_index()
            .sort_values("Tickets", ascending=False)
        )
        
        # Filter valid categories
        category_risk = category_risk[
            (category_risk[COL_CATEGORIZATION].notna()) & 
            (category_risk[COL_CATEGORIZATION] != "")
        ]
        
        if len(category_risk) > 0:
            # Add risk scoring based on actual priority data
            category_risk = category_risk.copy()  # Create explicit copy to avoid warnings
            category_risk["P1_P2_Incidents"] = category_risk["P1_Incidents"] + category_risk["P2_Incidents"]
            category_risk["High_Priority_Rate"] = (
                category_risk["P1_P2_Incidents"] / category_risk["Tickets"] * 100
            ).round(1)
            
            # Calculate risk score based on volume, SLA performance, and actual priority distribution
            category_risk["Risk_Score"] = (
                (category_risk["Tickets"] / 1000) * 0.3 +  # Volume weight
                ((1 - category_risk["SLA_Compliance"]) * 100) * 0.4 +  # SLA risk weight  
                (category_risk["High_Priority_Rate"] / 10) * 0.3  # High priority incident weight
            ).round(1)
            
            # Keep only storage analysis - removed charts and detailed category breakdowns
            
            # Storage infrastructure special analysis
            storage_categories = category_risk[category_risk[COL_CATEGORIZATION].str.contains("Storage", na=False)]
            if len(storage_categories) > 0:
                storage_tickets = storage_categories["Tickets"].sum()
                storage_sla = storage_categories["SLA_Compliance"].mean()
                
                st_subheader_with_popover(
                    "Storage Infrastructure Health",
                    """
                    **Purpose**: Monitor storage infrastructure performance as it represents 35% of all tickets.
                    
                    **Why Storage Matters**:
                    - **Business Impact**: Storage issues can affect all applications and services
                    - **Volume Indicator**: High ticket volume may indicate infrastructure aging or capacity issues
                    - **SLA Impact**: Storage problems can cascade to multiple business services
                    
                    **Action Thresholds**: SLA below 90% indicates need for infrastructure review or capacity planning.
                    """
                )
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Storage-Related Tickets", f"{storage_tickets:,}")
                with col2:
                    st.metric("Storage SLA Performance", f"{storage_sla:.1%}")
                
                if storage_sla < 0.90:
                    st.warning("⚠️ **Storage Alert**: Storage infrastructure SLA below 90% - may impact business operations")
                else:
                    st.success(f"✅ **Storage Health**: {storage_sla:.1%} SLA compliance - infrastructure performing well")
                
                # Strategic recommendation for storage
                storage_percentage = (storage_tickets / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
                if storage_percentage > 30:
                    st.info(f"📊 **Storage Focus**: {storage_percentage:.1f}% of all tickets - consider infrastructure modernization or capacity expansion")
        else:
            st.info("No categorization data available for risk analysis")
    else:
        st.info("Service category risk analysis not available - requires Categorization column in data")

def render_buma_sla_tab(filtered_df):
    """Renders the BUMA Contract SLA compliance tab."""
    
    # Calculate at-risk amount (configurable)
    monthly_service_charge = st.number_input(
        "Monthly Service Charge ($)", 
        value=187290, 
        help="Enter the monthly service charge to calculate at-risk amount (10% of monthly charges)"
    )
    at_risk_amount = monthly_service_charge * 0.10
    
    st.markdown(f"**At-Risk Amount**: ${at_risk_amount:,.2f} (10% of monthly service charges)")
    
    # BUMA Contract SLA Performance Summary
    st_header_with_popover(
        "BUMA Contract SLA Performance Dashboard - Section 24.10",
        """
        **Complete BUMA Contract SLA Implementation**:
        Based on exact specifications from Service Level Agreement Section 24.10
        
        **Total Service Level Credit Pool: 100%**
        - Incident Resolution: 46% (P1: 18%, P2: 12%, P3: 10%, P4: 6%)
        - Incident Response: 20% (P1: 8%, P2: 5%, P3: 4%, P4: 3%) 
        - Application Availability: 10%
        - Service Requests: 5%
        - Root Cause Analysis: 7% (P1: 4%, P2: 3%)
        - Service Desk Operations: 12% (tracked separately - not shown in this dashboard)
        
        **Performance Targets**:
        - Expected Level: 95% (aspirational, not penalized)
        - Minimum Level: 90% (contract requirement, penalized if below)
        - Exception: RCA requires 95% minimum (no expected level)
        
        **At-Risk Amount**: 10% of monthly service charges
        **Measurement**: Monthly periods with clock pausing for "Waiting For" states
        """
    )
    
    # Calculate SLA compliance by priority
    if len(filtered_df) == 0:
        st.warning("No data available for SLA analysis")
        return
        
    sla_performance = []
    total_financial_exposure = 0
    
    for priority in sorted(filtered_df[COL_PRIORITY_NUMERIC].unique()):
        priority_df = filtered_df[filtered_df[COL_PRIORITY_NUMERIC] == priority]
        
        if len(priority_df) == 0:
            continue
            
        # Resolution SLA
        resolution_compliance = priority_df[COL_SLA_MET].mean()
        resolution_target_expected = 0.95
        resolution_target_minimum = 0.90
        
        # Financial exposure calculation
        resolution_credit_pct = priority_df["Resolution_Credit_Pct"].iloc[0]
        response_credit_pct = priority_df["Response_Credit_Pct"].iloc[0]
        
        # Calculate potential penalties
        resolution_penalty = 0
        if resolution_compliance < resolution_target_minimum:
            resolution_penalty = at_risk_amount * (resolution_credit_pct / 100)
            
        # Response SLA (placeholder - would need actual response data)
        response_compliance = 0.95  # Placeholder
        response_penalty = 0
        if response_compliance < 0.90:
            response_penalty = at_risk_amount * (response_credit_pct / 100)
        
        total_penalty = resolution_penalty + response_penalty
        total_financial_exposure += total_penalty
        
        sla_performance.append({
            "Priority": f"P{priority}",
            "Total_Tickets": len(priority_df),
            "Resolution_Compliance": resolution_compliance,
            "Resolution_Target_Expected": resolution_target_expected,
            "Resolution_Target_Minimum": resolution_target_minimum,
            "Response_Compliance": response_compliance,
            "Resolution_Credit_Pct": resolution_credit_pct,
            "Response_Credit_Pct": response_credit_pct,
            "Resolution_Penalty": resolution_penalty,
            "Response_Penalty": response_penalty,
            "Total_Penalty": total_penalty,
            "Status": "✅ Pass" if resolution_compliance >= resolution_target_minimum else "❌ Fail"
        })
    
    # Display SLA Performance Summary
    perf_df = pd.DataFrame(sla_performance)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Financial Exposure", f"${total_financial_exposure:,.2f}")
    with col2:
        overall_compliance = filtered_df[COL_SLA_MET].mean()
        st.metric("Overall Resolution Compliance", f"{overall_compliance:.1%}")
    with col3:
        pass_count = sum(1 for p in sla_performance if p["Resolution_Compliance"] >= 0.90)
        st.metric("SLAs Meeting Minimum", f"{pass_count}/{len(sla_performance)}")
    
    # Resolution SLA Compliance Chart
    st_header_with_popover(
        "Resolution SLA Compliance vs Targets",
        """
        **BUMA Contract Resolution SLA Targets**:
        - P1: 90% within 4 hours (18% penalty weight)
        - P2: 90% within 8 hours (12% penalty weight)
        - P3: 90% within 5 business days/40 hours (10% penalty weight)
        - P4: 90% within 20 business days/160 hours (6% penalty weight)
        
        **Performance Levels**:
        - Expected Level: 95% compliance (aspirational target)
        - Minimum Level: 90% compliance (contract requirement)
        - Below minimum triggers financial penalties
        
        **Chart Elements**: 
        - Green dashed line: Expected target (95%)
        - Red dashed line: Minimum acceptable (90%)
        - Blue bars: Actual compliance per priority level
        - Values based on (Resolved - Opened) time vs SLA targets
        """
    )
    
    fig_resolution = px.bar(
        perf_df, 
        x="Priority", 
        y="Resolution_Compliance",
        title="Resolution SLA Compliance by Priority",
        labels={"Resolution_Compliance": "SLA Compliance Rate"},
        text=perf_df["Resolution_Compliance"].map("{:.1%}".format)
    )
    
    # Add target lines
    fig_resolution.add_hline(y=0.95, line_dash="dash", line_color="green", 
                           annotation_text="Expected Target (95%)")
    fig_resolution.add_hline(y=0.90, line_dash="dash", line_color="red", 
                           annotation_text="Minimum Target (90%)")
    
    fig_resolution.update_layout(yaxis_tickformat=".0%")
    fig_resolution.update_traces(textposition="outside")
    st.plotly_chart(fig_resolution, use_container_width=True)
    
    # Financial Impact Analysis
    st_header_with_popover(
        "Financial Impact Analysis",
        """
        **Financial Penalty Framework**:
        - At-risk amount: 10% of monthly service charges (configurable above)
        - Total credit pool cannot exceed at-risk amount
        - Penalties applied only when performance falls below 90% minimum
        
        **Resolution SLA Credit Percentages**:
        - P1: 18% of at-risk amount (highest impact)
        - P2: 12% of at-risk amount
        - P3: 10% of at-risk amount
        - P4: 6% of at-risk amount
        
        **Additional Penalty Sources** (not shown in chart):
        - Response SLAs: P1(8%), P2(5%), P3(4%), P4(3%)
        - Service desk metrics: 4% each (email, phone speed, abandonment)
        - Application availability: 10%
        - RCA completion: P1(4%), P2(3%)
        
        **Calculation**: Only applied when compliance < 90% minimum threshold
        """
    )
    
    fig_financial = px.bar(
        perf_df,
        x="Priority",
        y="Total_Penalty", 
        title="Potential Monthly Financial Penalties by Priority",
        labels={"Total_Penalty": "Penalty Amount ($)"},
        text=perf_df["Total_Penalty"].map("${:,.0f}".format)
    )
    fig_financial.update_traces(textposition="outside")
    st.plotly_chart(fig_financial, use_container_width=True)
    
    # Detailed SLA Performance Table
    st_subheader_with_popover(
        "Detailed SLA Performance Breakdown",
        """
        **Column Definitions**:
        - **Priority**: P1-P4 incident priority levels
        - **Total_Tickets**: Count of incidents at this priority level
        - **Resolution_Compliance**: Actual % resolved within SLA timeframe
        - **Resolution_Target_Expected**: 95% aspiration level (not penalized)
        - **Resolution_Target_Minimum**: 90% contract requirement (penalty if below)
        - **Resolution_Penalty**: Financial exposure if compliance < 90%
        - **Status**: ✅ Pass (≥90%) | ❌ Fail (<90%)
        
        **Data Source**: Calculated from ticket export timestamps (Opened → Resolved)
        
        **SLA Timeframes**:
        - P1: 4 hours | P2: 8 hours | P3: 40 hours (5 business days) | P4: 160 hours (20 business days)
        
        **Financial Impact**: Penalties only apply when minimum (90%) threshold is breached
        """
    )
    
    display_cols = ["Priority", "Total_Tickets", "Resolution_Compliance", 
                   "Resolution_Target_Expected", "Resolution_Target_Minimum", 
                   "Resolution_Penalty", "Status"]
    st.dataframe(perf_df[display_cols].round(3))
    
    
    # Application Availability
    st_header_with_popover(
        "Application Availability (ERP)",
        """
        **BUMA Contract Application SLA**:
        - Expected Level: 99.25% monthly uptime
        - Minimum Level: 99.00% monthly uptime
        - Penalty Weight: 10% of at-risk amount (high impact)
        
        **Data Requirements**:
        - System monitoring tools (e.g., SCOM, SolarWinds, Datadog)
        - Application performance monitoring (APM)
        - Infrastructure monitoring dashboards
        - Current value: Placeholder (99.15% - would trigger discussion but no penalty)
        
        **Calculation Method**:
        - Total monthly minutes - downtime minutes / total monthly minutes
        - Planned maintenance windows may be excluded (contract dependent)
        - 99.00% = ~7.2 hours downtime per month maximum
        - 99.25% = ~5.4 hours downtime per month target
        
        **Integration**: Requires automated monitoring system data feeds
        """
    )
    
    # Application Availability (Placeholder - would need monitoring data)
    app_availability = 99.15  # Placeholder percentage
    availability_target_expected = 99.25
    availability_target_minimum = 99.00
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Availability", f"{app_availability:.2f}%")
    with col2:
        st.metric("Expected Target", f"{availability_target_expected:.2f}%")
    with col3:
        availability_penalty = 0
        if app_availability < availability_target_minimum:
            availability_penalty = at_risk_amount * 0.10
        st.metric("Potential Penalty", f"${availability_penalty:,.2f}")
    
    # Root Cause Analysis Tracking
    st_header_with_popover(
        "Root Cause Analysis (RCA) Tracking - SLAs 10, 11",
        """
        **Section 24.10 RCA Requirements**:
        
        **SLA #10 - P1 RCA**: 
        - Expected: 95% within 5 business days | Minimum: 95% within 5 business days
        - Credit: 4% of at-risk amount
        
        **SLA #11 - P2 RCA**:
        - Expected: 95% within 10 business days | Minimum: 95% within 10 business days  
        - Credit: 3% of at-risk amount
        
        **Contract Note**: RCA has no distinction between expected/minimum levels - 
        both require 95% compliance (higher standard than other SLAs)
        
        **Calculation Logic (Data-Driven Assumption)**:
        - RCA completion assumed when incident resolved within SLA timeframe
        - Rationale: Proper incident management includes RCA during resolution
        - Fast resolution indicates structured process likely included RCA
        - Delayed resolution may indicate process gaps affecting RCA timing
        
        **Total RCA Impact**: 7% of at-risk amount (P1: 4%, P2: 3%)
        """
    )
    
    # RCA Tracking - Using resolution time as proxy for RCA completion
    def calculate_rca_metrics(priority_num, rca_target_days):
        priority_tickets = filtered_df[filtered_df[COL_PRIORITY_NUMERIC] == priority_num]
        
        if len(priority_tickets) == 0:
            return None
            
        # Assume RCA completed on-time if resolution was within SLA
        rca_completed_ontime = len(priority_tickets[priority_tickets[COL_SLA_MET] == True])
        total_incidents = len(priority_tickets)
        rca_compliance = rca_completed_ontime / total_incidents if total_incidents > 0 else 0
        
        # Calculate penalty
        penalty_pct = 0.04 if priority_num == 1 else 0.03
        penalty = 0 if rca_compliance >= 0.95 else at_risk_amount * penalty_pct
        
        return {
            "Priority": f"P{priority_num}",
            "Total_Incidents": total_incidents,
            "RCA_Required": total_incidents,
            "RCA_Completed_OnTime": rca_completed_ontime,
            "Target": f"95% within {rca_target_days} days",
            "Compliance": f"{rca_compliance:.1%}",
            "Status": "✅ Pass" if rca_compliance >= 0.95 else "❌ Fail",
            "Penalty_Risk": f"${penalty:,.2f}",
            "Logic": "Based on resolution SLA compliance"
        }
    
    rca_metrics = []
    
    # P1 RCA (5 business days)
    p1_rca = calculate_rca_metrics(1, 5)
    if p1_rca:
        rca_metrics.append(p1_rca)
    
    # P2 RCA (10 business days)  
    p2_rca = calculate_rca_metrics(2, 10)
    if p2_rca:
        rca_metrics.append(p2_rca)
    
    if rca_metrics:
        rca_df = pd.DataFrame(rca_metrics)
        st.dataframe(rca_df, use_container_width=True)
        
        # Update total financial exposure with RCA penalties
        rca_total_penalty = sum(float(rca["Penalty_Risk"].replace("$", "").replace(",", "")) for rca in rca_metrics)
        st.info(f"💰 **Additional RCA Penalty Exposure**: ${rca_total_penalty:,.2f}")
        st.info(f"🔢 **Updated Total Financial Exposure**: ${total_financial_exposure + rca_total_penalty:,.2f}")
        
        # Add explanation of the logic
        with st.expander("📋 RCA Calculation Logic Details"):
            st.markdown("""
            **Assumption Rationale**:
            - Incidents resolved within SLA likely followed proper incident management processes
            - RCA is typically completed as part of incident closure for timely resolutions
            - Delayed resolutions may indicate process issues that could delay RCA
            
            **Calculation**:
            1. Count total P1/P2 incidents requiring RCA
            2. Count incidents resolved within resolution SLA timeframe  
            3. Assume those resolved on-time also completed RCA on-time
            4. Calculate compliance percentage against 95% target
            5. Apply penalty if below 95% threshold
            
            **Benefits**:
            - Uses available data from ticket exports
            - Provides meaningful RCA performance indicator
            - Incentivizes both fast resolution AND proper incident management
            """)
    else:
        st.info("No P1 or P2 incidents found for RCA analysis")
    
    # Service Request Resolution Tracking
    st_header_with_popover(
        "Service Request Resolution - SLA 9",
        """
        **Section 24.10 Service Request SLA**:
        
        **SLA #9 - Service Request Resolution**:
        - Expected: 95% within agreed timeframe
        - Minimum: 90% within agreed timeframe  
        - Credit: 5% of at-risk amount
        
        **Calculation**: (Service Requests completed on time / Total Service Requests) × 100
        
        **Data Challenge**: 
        - Requires service request categorization in ticket data
        - Needs agreed timeframe definition per request type
        - Current implementation: Placeholder pending data classification
        
        **Note**: Service requests are distinct from incidents and require separate tracking
        """
    )
    
    # Service Request Metrics (Using actual SR Result field from TCD data)
    total_tickets = len(filtered_df)
    
    # Actual service request identification using SR Result field
    if COL_SR_RESULT in filtered_df.columns:
        actual_service_requests = filtered_df[filtered_df[COL_SR_RESULT] == "TRUE"]
        num_service_requests = len(actual_service_requests)
        
        if num_service_requests > 0:
            # Calculate service request compliance (placeholder for agreed timeframes)
            # In real implementation, would need agreed timeframe per request type
            sr_compliance = actual_service_requests[COL_SLA_MET].mean()
        else:
            sr_compliance = 1.0  # No service requests to fail
    else:
        # Fallback to old estimation if SR Result column not available
        num_service_requests = max(1, int(total_tickets * 0.3))
        sr_compliance = 0.92
    
    service_request_penalty = 0
    if sr_compliance < 0.90:
        service_request_penalty = at_risk_amount * 0.05
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Service Requests", f"{num_service_requests:,}")
    with col2:
        st.metric("SR Compliance", f"{sr_compliance:.1%}")
    with col3:
        st.metric("Potential Penalty", f"${service_request_penalty:,.2f}")
    
    if COL_SR_RESULT in filtered_df.columns:
        sr_percentage = (num_service_requests / total_tickets * 100) if total_tickets > 0 else 0
        st.success(f"✅ **Using Actual Data**: {num_service_requests:,} service requests identified ({sr_percentage:.1f}% of total tickets)")
    else:
        st.info("🔄 **Using Estimation**: Service request identification requires SR Result field in data")
    
    # Clock Pausing and Contract Notes
    st_header_with_popover(
        "Contract Implementation Notes",
        """
        **Section 24.10 Key Contract Provisions**:
        
        **Clock Pausing Logic**:
        - Resolution SLA timers pause when ticket is in "Waiting For" state
        - Includes waiting for customer response, vendor response, scheduled maintenance
        - Current calculation limitation: Uses total resolution time (no pause adjustment)
        - Real implementation requires workflow state change tracking
        
        **Excused Performance Conditions**:
        - Force Majeure events
        - BUMA-caused failures or delays  
        - Accenture-approved service reductions
        - Volume spikes exceeding baseline by >10%
        - Vendor/third-party caused outages
        
        **Earn-Back Provision**:
        - Service level credits can be recovered
        - Requires 2 consecutive months exceeding targets after failure
        - Encourages sustained performance improvement
        
        **Measurement Periods**:
        - All SLAs measured monthly
        - Business days: Monday-Friday, Brisbane business hours
        - Excludes Queensland public holidays
        """
    )
    
    # Update total financial exposure with all components
    total_resolution_penalty = sum(float(p["Total_Penalty"]) for p in sla_performance)
    rca_penalty = sum(float(rca["Penalty_Risk"].replace("$", "").replace(",", "")) for rca in rca_metrics) if rca_metrics else 0
    service_desk_penalty = 0  # Service desk section removed
    
    # Add service request and app availability penalties (placeholders)
    app_availability_penalty = availability_penalty if 'availability_penalty' in locals() else 0
    
    total_exposure = total_resolution_penalty + rca_penalty + service_desk_penalty + service_request_penalty + app_availability_penalty
    
    st.markdown("---")
    st_header_with_popover(
        "Total Monthly Financial Exposure Summary",
        """
        **SLA Financial Impact Breakdown (Tracked in Dashboard)**:
        
        **Resolution SLAs (46%)**: P1(18%) + P2(12%) + P3(10%) + P4(6%)
        **Response SLAs (20%)**: P1(8%) + P2(5%) + P3(4%) + P4(3%) 
        **Application Availability (10%)**: ERP uptime minimum 99.00%
        **Service Requests (5%)**: Completion within agreed timeframes
        **Root Cause Analysis (7%)**: P1 RCA(4%) + P2 RCA(3%)
        
        **Service Desk (12%)**: Phone abandonment(4%) + Email response(4%) + Phone speed(4%) - tracked separately
        
        **Total Pool**: 100% of at-risk amount (10% of monthly service charges)
        **Penalty Trigger**: Performance below minimum thresholds
        """
    )
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Resolution Penalties", f"${total_resolution_penalty:,.2f}")
    with col2:
        st.metric("RCA Penalties", f"${rca_penalty:,.2f}")
    with col3:
        st.metric("Service Request Penalties", f"${service_request_penalty:,.2f}")
    with col4:
        st.metric("**TOTAL EXPOSURE**", f"**${total_exposure:,.2f}**")
    
    exposure_percentage = (total_exposure / at_risk_amount) * 100 if at_risk_amount > 0 else 0
    if exposure_percentage > 0:
        st.warning(f"⚠️ **Financial Risk**: {exposure_percentage:.1f}% of at-risk amount (${at_risk_amount:,.2f})")
    else:
        st.success("✅ **All SLAs Meeting Minimum Requirements** - No financial penalties")

def render_performance_tab(filtered_df):
    """Renders the content for the Performance Analysis tab."""
    st_header_with_popover(
        "SLA Compliance Analysis",
        """
        **Purpose**: Monitor service level agreement performance across different priority levels to ensure customer commitments are met.
        
        **Key Insights**:
        - P1: 90% within 4 hours
        - P2: 90% within 8 hours  
        - P3: 90% within 5 business days (40 hours)
        - P4: 90% within 20 business days (160 hours)
        - Priority-based performance gaps
        - Overall service quality metrics
        """
    )
    
    sla_compliance = (
        filtered_df.groupby(COL_PRIORITY)
        .agg(
            Total_Tickets=(COL_NUMBER, "count"),
            SLA_Met_Count=(COL_SLA_MET, "sum"),
            Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean")
        )
        .reset_index()
    )
    if sla_compliance['Total_Tickets'].sum() > 0:
        sla_compliance["SLA_Compliance"] = sla_compliance["SLA_Met_Count"] / sla_compliance["Total_Tickets"]
    else:
        sla_compliance["SLA_Compliance"] = 0.0

    fig2 = px.bar(sla_compliance, x=COL_PRIORITY, y="SLA_Compliance",
                  text=sla_compliance["SLA_Compliance"].map("{:.1%}".format),
                  title="SLA Compliance by Priority Level",
                  labels={"SLA_Compliance": "SLA Compliance Rate"})
    fig2.update_layout(yaxis_tickformat=".0%")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    st_subheader_with_popover(
        "SLA Compliance Details",
        """
        **Purpose**: Detailed breakdown of SLA performance metrics by priority level.
        
        **Columns Explained**:
        - Total_Tickets: Number of tickets for this priority
        - SLA_Met_Count: How many met their SLA target
        - Avg_Resolution_Hours: Average time to resolve
        - SLA_Compliance: Percentage meeting SLA (SLA_Met_Count/Total_Tickets)
        """
    )
    # Format SLA_Compliance as percentage
    sla_display = sla_compliance.copy()
    if 'SLA_Compliance' in sla_display.columns:
        sla_display['SLA_Compliance'] = sla_display['SLA_Compliance'].map('{:.1%}'.format)
    sla_display = sla_display.round(2)
    st.dataframe(sla_display)

    st_header_with_popover(
        "Assignment Group Performance",
        """
        **Purpose**: Analyze team performance, workload distribution, and identify high-performing or struggling groups.
        
        **Key Insights**:
        - Workload balance across teams
        - Team efficiency comparisons
        - Resource allocation optimization
        """
    )
    
    group_perf = (
        filtered_df.groupby(COL_ASSIGNMENT_GROUP)
        .agg(
            Tickets=(COL_NUMBER, "count"),
            Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
            SLA_Compliance=(COL_SLA_MET, "mean")
        )
        .reset_index()
        .sort_values("Tickets", ascending=False)
    )
    top_groups = group_perf.head(15)

    st_subheader_with_popover(
        "Top 15 Assignment Groups by Ticket Volume",
        """
        **Purpose**: Identify teams handling the most tickets to understand workload distribution.
        
        **Graph Explanation**: Bar chart showing ticket count per assignment group. Taller bars indicate teams with higher workloads. Text labels show exact ticket counts.
        """
    )
    fig3 = px.bar(top_groups, x=COL_ASSIGNMENT_GROUP, y="Tickets",
                  text_auto=True,
                  title="Top 15 Assignment Groups by Ticket Volume")
    fig3.update_xaxes(tickangle=45)
    st.plotly_chart(fig3, use_container_width=True)

    st_subheader_with_popover(
        "Assignment Group SLA Performance (Top 15)",
        """
        **Purpose**: Compare team efficiency by plotting resolution time vs SLA compliance.
        
        **Graph Explanation**: Bubble scatter plot where:
        - X-axis: Average resolution time (lower is better)
        - Y-axis: SLA compliance rate (higher is better)
        - Bubble size: Total ticket volume (larger = more tickets)
        - Top-right quadrant = high performance (fast + compliant)
        """
    )
    fig4 = px.scatter(top_groups, x="Avg_Resolution_Hours", y="SLA_Compliance",
                      size="Tickets", hover_name=COL_ASSIGNMENT_GROUP,
                      title="Assignment Group Performance: Resolution Time vs SLA Compliance",
                      labels={"Avg_Resolution_Hours": "Average Resolution Hours", 
                             "SLA_Compliance": "SLA Compliance Rate"})
    fig4.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig4, use_container_width=True)

    # Tower Performance Analysis (Enhanced with TCD data)
    if COL_TOWER in filtered_df.columns:
        st_header_with_popover(
            "Tower Performance Analysis",
            """
            **Purpose**: Analyze performance across organizational towers for strategic resource allocation.
            
            **Towers**:
            - **IO (Infrastructure Operations)**: Server, network, infrastructure incidents
            - **AO (Application Operations)**: SAP, business application issues  
            - **L3 (Level 3 Support)**: Complex technical escalations
            - **Others**: Service Desk, WFS, Cloud, specialized teams
            
            **Key Insights**:
            - Tower workload distribution and capacity planning
            - Performance benchmarking across service areas
            - Resource allocation optimization opportunities
            """
        )
        
        # Calculate tower performance metrics
        tower_perf = (
            filtered_df.groupby(COL_TOWER)
            .agg(
                Tickets=(COL_NUMBER, "count"),
                Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
                SLA_Compliance=(COL_SLA_MET, "mean")
            )
            .reset_index()
            .sort_values("Tickets", ascending=False)
        )
        
        # Filter out invalid/missing tower values
        tower_perf = tower_perf[
            (~tower_perf[COL_TOWER].isin(['#N/A', '', ' '])) & 
            (tower_perf[COL_TOWER].notna())
        ]
        
        if len(tower_perf) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st_subheader_with_popover(
                    "Tower Workload Distribution",
                    """
                    **Purpose**: Understand organizational workload distribution for resource planning.
                    
                    **Tower Definitions**:
                    - **IO**: Infrastructure Operations (servers, networks, storage)
                    - **AO**: Application Operations (SAP, business applications)
                    - **L3**: Level 3 Support (complex escalations, specialized expertise)
                    
                    **Key Insights**: Uneven distribution may indicate need for resource rebalancing or skill development.
                    """
                )
                fig_tower_volume = px.pie(
                    tower_perf, 
                    names=COL_TOWER, 
                    values="Tickets",
                    title="Ticket Distribution by Tower"
                )
                st.plotly_chart(fig_tower_volume, use_container_width=True)
            
            with col2:
                st_subheader_with_popover(
                    "Tower SLA Performance",
                    """
                    **Purpose**: Compare SLA compliance across organizational towers to identify performance gaps.
                    
                    **Graph Explanation**: Bar chart showing SLA compliance percentage by tower. Higher bars indicate better performance. Text labels show exact compliance rates.
                    
                    **Key Insights**: Towers with low compliance may need additional resources, training, or process improvements.
                    """
                )
                fig_tower_sla = px.bar(
                    tower_perf, 
                    x=COL_TOWER, 
                    y="SLA_Compliance",
                    title="SLA Compliance by Tower",
                    text=tower_perf["SLA_Compliance"].map("{:.1%}".format)
                )
                fig_tower_sla.update_layout(yaxis_tickformat=".0%")
                fig_tower_sla.update_traces(textposition="outside")
                fig_tower_sla.update_xaxes(tickangle=45)
                st.plotly_chart(fig_tower_sla, use_container_width=True)
            
            st_subheader_with_popover(
                "Detailed Tower Performance",
                """
                **Purpose**: Comprehensive tower metrics for strategic planning and performance management.
                
                **Columns Explained**:
                - **Tickets**: Total volume handled by each tower
                - **Avg_Resolution_Hours**: Average time to resolve (efficiency indicator)
                - **SLA_Compliance**: Percentage meeting SLA targets (quality indicator)
                
                **Use Case**: Identify high-performing towers for best practice sharing and underperforming areas for improvement focus.
                """
            )
            tower_display = tower_perf.copy()
            if 'SLA_Compliance' in tower_display.columns:
                tower_display['SLA_Compliance'] = tower_display['SLA_Compliance'].map('{:.1%}'.format)
            tower_display = tower_display.round(2)
            st.dataframe(tower_display, use_container_width=True)
            
            # Tower Performance Insights
            st.write("#### Tower Performance Insights")
            if len(tower_perf) > 0:
                best_tower = tower_perf.loc[tower_perf['SLA_Compliance'].idxmax()]
                worst_tower = tower_perf.loc[tower_perf['SLA_Compliance'].idxmin()]
                highest_volume = tower_perf.loc[tower_perf['Tickets'].idxmax()]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success(f"🏆 **Top Performer**: {best_tower[COL_TOWER]} ({best_tower['SLA_Compliance']:.1%} SLA)")
                with col2:
                    if worst_tower['SLA_Compliance'] < 0.85:
                        st.warning(f"⚠️ **Needs Attention**: {worst_tower[COL_TOWER]} ({worst_tower['SLA_Compliance']:.1%} SLA)")
                    else:
                        st.info(f"📊 **Monitor**: {worst_tower[COL_TOWER]} ({worst_tower['SLA_Compliance']:.1%} SLA)")
                with col3:
                    st.info(f"📈 **Highest Volume**: {highest_volume[COL_TOWER]} ({highest_volume['Tickets']:,} tickets)")
                
                # Strategic recommendations
                avg_sla = tower_perf['SLA_Compliance'].mean()
                if avg_sla < 0.90:
                    st.warning("⚠️ **Strategic Alert**: Overall tower SLA performance below 90% - consider resource rebalancing")
                
                workload_imbalance = tower_perf['Tickets'].std() / tower_perf['Tickets'].mean()
                if workload_imbalance > 0.5:
                    st.info("📊 **Insight**: High workload variation across towers - consider redistribution for efficiency")
        else:
            st.info("No valid tower data available for analysis")
    else:
        st.info("Tower analysis not available - requires Tower column in data")

    # Geographic Service Delivery Analysis
    st_header_with_popover(
        "Geographic Service Delivery Performance",
        """
        **Purpose**: Monitor service delivery performance across BUMA's geographic locations, with focus on mining site operations.
        
        **Location Categories**:
        - **Brisbane HQ**: Primary office location (30% of tickets)
        - **Mining Sites**: Meandu, Blackwater, Goonyella, Saraji (15% of tickets)
        - **Regional Offices**: Australia East, Philippines operations (39% of tickets)
        - **Other Locations**: Various operational sites (16% of tickets)
        
        **Key Insights**:
        - Mining site-specific SLA performance for operational continuity
        - Regional resource allocation optimization
        - Location-based incident pattern analysis
        - Geographic risk assessment for business operations
        """
    )
    
    # Calculate geographic performance metrics
    location_perf = (
        filtered_df.groupby(COL_LOCATION)
        .agg(
            Tickets=(COL_NUMBER, "count"),
            Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
            SLA_Compliance=(COL_SLA_MET, "mean"),
            P1_Tickets=(COL_PRIORITY_NUMERIC, lambda x: (x == 1).sum()),
            P2_Tickets=(COL_PRIORITY_NUMERIC, lambda x: (x == 2).sum())
        )
        .reset_index()
        .sort_values("Tickets", ascending=False)
    )
    
    # Filter out empty/invalid locations
    location_perf = location_perf[
        (location_perf[COL_LOCATION].notna()) & 
        (location_perf[COL_LOCATION] != "")
    ]
    
    if len(location_perf) > 0:
        # Identify mining sites and key locations
        location_perf = location_perf.copy()  # Create explicit copy to avoid warnings
        mining_sites = ["Meandu", "Blackwater", "Goonyella", "Saraji", "Goonyella North", "Commodore", "Burton Complex"]
        location_perf["Location_Type"] = location_perf[COL_LOCATION].apply(
            lambda x: "Mining Site" if x in mining_sites 
            else "HQ" if x == "Brisbane" 
            else "Regional" if x in ["Australia East", "Philippines", "Australia", "Australia Southeast"]
            else "Other"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### Top 10 Locations by Volume")
            top_locations = location_perf.head(10)
            fig_loc_volume = px.bar(
                top_locations, 
                x="Tickets", 
                y=COL_LOCATION,
                title="Ticket Volume by Location",
                text="Tickets",
                color="Location_Type",
                color_discrete_map={
                    "Mining Site": "#ff6b6b", 
                    "HQ": "#4ecdc4", 
                    "Regional": "#45b7d1", 
                    "Other": "#96ceb4"
                }
            )
            fig_loc_volume.update_traces(textposition="outside")
            fig_loc_volume.update_layout(height=500)
            st.plotly_chart(fig_loc_volume, use_container_width=True)
        
        with col2:
            st.write("#### SLA Performance by Location Type")
            location_type_summary = (
                location_perf.groupby("Location_Type")
                .agg(
                    Total_Tickets=("Tickets", "sum"),
                    Avg_SLA_Compliance=("SLA_Compliance", "mean"),
                    Locations=("Location_Type", "count")
                )
                .reset_index()
            )
            
            fig_loc_sla = px.bar(
                location_type_summary,
                x="Location_Type",
                y="Avg_SLA_Compliance", 
                title="Average SLA Compliance by Location Type",
                text=location_type_summary["Avg_SLA_Compliance"].map("{:.1%}".format),
                color="Avg_SLA_Compliance",
                color_continuous_scale="RdYlGn"
            )
            fig_loc_sla.update_layout(yaxis_tickformat=".0%")
            fig_loc_sla.update_traces(textposition="outside")
            st.plotly_chart(fig_loc_sla, use_container_width=True)
        
        # Mining Sites Deep Dive
        mining_locations = location_perf[location_perf["Location_Type"] == "Mining Site"].copy()
        if len(mining_locations) > 0:
            st.write("#### Mining Sites Performance Dashboard")
            
            # Mining locations analysis (removed critical ticket calculations)
            
            # Display mining sites table (excluding critical ticket columns)
            mining_display_cols = [COL_LOCATION, "Tickets", "SLA_Compliance", "Avg_Resolution_Hours"]
            mining_display = mining_locations[mining_display_cols].copy()
            if 'SLA_Compliance' in mining_display.columns:
                mining_display['SLA_Compliance'] = mining_display['SLA_Compliance'].map('{:.1%}'.format)
            mining_display = mining_display.round(2)
            st.dataframe(mining_display, use_container_width=True)
            
            # Mining site insights
            total_mining_tickets = mining_locations["Tickets"].sum()
            avg_mining_sla = mining_locations["SLA_Compliance"].mean()
            avg_resolution_hours = mining_locations["Avg_Resolution_Hours"].mean()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Mining Site Tickets", f"{total_mining_tickets:,}")
            with col2:
                st.metric("Avg Mining SLA Compliance", f"{avg_mining_sla:.1%}")
            with col3:
                st.metric("Avg Resolution Time", f"{avg_resolution_hours:.1f}h")
            
            if avg_mining_sla < 0.90:
                st.warning("⚠️ **Mining Site Alert**: SLA compliance below 90% minimum - may impact operations")
            else:
                st.success("✅ **Mining Operations**: SLA compliance within acceptable range")
            
            # Additional Mining Site Insights
            if len(mining_locations) > 1:
                best_mining_site = mining_locations.loc[mining_locations['SLA_Compliance'].idxmax()]
                worst_mining_site = mining_locations.loc[mining_locations['SLA_Compliance'].idxmin()]
                fastest_site = mining_locations.loc[mining_locations['Avg_Resolution_Hours'].idxmin()]
                
                st.write("#### Mining Site Performance Analysis")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success(f"🏆 **Best SLA Performance**: {best_mining_site[COL_LOCATION]} ({best_mining_site['SLA_Compliance']:.1%})")
                with col2:
                    if worst_mining_site['SLA_Compliance'] < 0.85:
                        st.warning(f"⚠️ **Site Alert**: {worst_mining_site[COL_LOCATION]} ({worst_mining_site['SLA_Compliance']:.1%}) - below target")
                    else:
                        st.info(f"📊 **Monitor**: {worst_mining_site[COL_LOCATION]} ({worst_mining_site['SLA_Compliance']:.1%}) - lowest SLA")
                with col3:
                    st.info(f"⚡ **Fastest Resolution**: {fastest_site[COL_LOCATION]} ({fastest_site['Avg_Resolution_Hours']:.1f}h avg)")
        
        st_subheader_with_popover(
            "Complete Geographic Performance",
            """
            **Purpose**: Comprehensive view of service delivery performance across all BUMA locations.
            
            **Columns Explained**:
            - **Location_Type**: Classification (Mining Site, HQ, Regional, Other)
            - **Tickets**: Volume of issues from this location
            - **SLA_Compliance**: Service level performance rate
            - **Avg_Resolution_Hours**: Average resolution efficiency
            - **P1_Tickets/P2_Tickets**: Critical incident counts
            
            **Strategic Value**: Identify locations requiring infrastructure investment, additional support resources, or process improvements.
            """
        )
        geo_display_cols = [COL_LOCATION, "Location_Type", "Tickets", "SLA_Compliance", 
                          "Avg_Resolution_Hours", "P1_Tickets", "P2_Tickets"]
        geo_display = location_perf[geo_display_cols].head(15).copy()
        if 'SLA_Compliance' in geo_display.columns:
            geo_display['SLA_Compliance'] = geo_display['SLA_Compliance'].map('{:.1%}'.format)
        geo_display = geo_display.round(2)
        st.dataframe(geo_display, use_container_width=True)
    else:
        st.info("No location data available for geographic analysis")

    st_header_with_popover(
        "Resolution Time Analysis",
        """
        **Purpose**: Analyze resolution efficiency across priorities and channels to identify bottlenecks and improve service delivery.
        
        **Key Insights**:
        - Priority-based resolution patterns
        - Channel efficiency comparisons
        - Performance outliers and extremes
        """
    )

    if len(filtered_df) > 0:
        res_quantile = filtered_df[COL_RESOLUTION_HOURS].quantile(0.95)
        resolution_filtered = filtered_df[filtered_df[COL_RESOLUTION_HOURS] <= res_quantile]
    else:
        resolution_filtered = filtered_df

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Resolution Time by Priority")
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Compare resolution time distributions across priority levels.
            **Box Plot Elements**: Center line (Median), Box (IQR), Whiskers (1.5xIQR), Dots (Outliers).
            **Interpretation**: Smaller boxes = more consistent resolution times.
            """)
        
        # Sort priorities for consistent chart ordering
        priority_order = sorted([p for p in resolution_filtered[COL_PRIORITY].unique() if pd.notna(p)])
        fig7 = px.box(resolution_filtered, x=COL_PRIORITY, y=COL_RESOLUTION_HOURS,
                      title="Resolution Time Distribution by Priority",
                      labels={COL_RESOLUTION_HOURS: "Resolution Time (Hours)"},
                      category_orders={COL_PRIORITY: priority_order})
        st.plotly_chart(fig7, use_container_width=True)
    with col2:
        st.markdown("#### Resolution Time by Channel")
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Compare resolution efficiency across different submission channels.
            **Interpretation**: Channels with lower medians and smaller boxes indicate more efficient processing.
            """)
        
        top_channels = []
        if len(filtered_df) > 0:
            top_channels = filtered_df[COL_CHANNEL].value_counts().head(5).index
            channel_filtered = resolution_filtered[resolution_filtered[COL_CHANNEL].isin(top_channels)]
        else:
            channel_filtered = filtered_df
        
        fig8 = px.box(channel_filtered, x=COL_CHANNEL, y=COL_RESOLUTION_HOURS,
                      title="Resolution Time by Top 5 Channels",
                      labels={COL_RESOLUTION_HOURS: "Resolution Time (Hours)"},
                      category_orders={COL_CHANNEL: top_channels})
        
        # Word wrap long channel names, specifically "Auto-Generated Event"
        fig8.update_xaxes(
            tickangle=0,
            tickmode='array',
            tickvals=list(range(len(top_channels))),
            ticktext=[channel.replace('Auto-Generated Event', 'Auto-<br>Generated<br>Event') 
                     if 'Auto-Generated Event' in channel else channel 
                     for channel in top_channels]
        )
        st.plotly_chart(fig8, use_container_width=True)
        
    st_header_with_popover(
        "Top Assignee Performance",
        """
        **Purpose**: Recognize high performers and identify individual workload distribution and performance patterns.
        
        **Key Insights**:
        - Individual performance metrics
        - Workload distribution fairness
        - Recognition and development opportunities
        """
    )
    assignee_perf = (
        filtered_df.groupby(COL_ASSIGNED_TO)
        .agg(
            Tickets=(COL_NUMBER, "count"),
            Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
            SLA_Compliance=(COL_SLA_MET, "mean")
        )
        .reset_index()
        .sort_values("Tickets", ascending=False)
        .head(20)
    )
    st_subheader_with_popover(
        "Top 20 Assignees by Ticket Volume",
        """
        **Purpose**: Individual performance analysis and workload distribution.
        
        **Metrics Explained**:
        - **Tickets**: Total assigned tickets
        - **Avg_Resolution_Hours**: Individual efficiency metric
        - **SLA_Compliance**: Personal SLA performance rate
        """
    )
    # Format SLA_Compliance as percentage
    assignee_display = assignee_perf.copy()
    if 'SLA_Compliance' in assignee_display.columns:
        assignee_display['SLA_Compliance'] = assignee_display['SLA_Compliance'].map('{:.1%}'.format)
    assignee_display = assignee_display.round(2)
    st.dataframe(assignee_display)
    
    # Top Assignee Performance Insights
    if len(assignee_perf) > 0:
        st.write("#### Individual Performance Insights")
        
        # Find top performers
        high_volume_assignees = assignee_perf[assignee_perf['Tickets'] >= assignee_perf['Tickets'].quantile(0.75)]
        top_sla_performers = assignee_perf[assignee_perf['SLA_Compliance'] >= 0.95]
        
        col1, col2 = st.columns(2)
        with col1:
            if len(top_sla_performers) > 0:
                top_performer = top_sla_performers.iloc[0][COL_ASSIGNED_TO]
                top_sla = top_sla_performers.iloc[0]['SLA_Compliance']
                st.success(f"🌟 **Top SLA Performer**: {top_performer} ({top_sla:.1%})")
            
        with col2:
            if len(high_volume_assignees) > 0:
                high_volume_performer = high_volume_assignees.iloc[0][COL_ASSIGNED_TO]
                volume = high_volume_assignees.iloc[0]['Tickets']
                st.info(f"📊 **Highest Volume**: {high_volume_performer} ({volume:,} tickets)")
        
        # Workload distribution analysis
        avg_tickets = assignee_perf['Tickets'].mean()
        std_tickets = assignee_perf['Tickets'].std()
        cv = std_tickets / avg_tickets if avg_tickets > 0 else 0
        
        if cv > 0.5:
            st.warning("⚠️ **Workload Imbalance**: High variation in ticket assignments - consider workload redistribution")
        else:
            st.success("✅ **Balanced Workload**: Relatively even ticket distribution across assignees")

def render_categorical_tab(filtered_df):
    """Renders the content for the Categorical Analysis tab."""
    st_header_with_popover(
        "Monthly Ticket Channel Breakdown",
        """
        **Purpose**: To visualize the breakdown of ticket volumes by channel over time, similar to the provided Excel analysis.
        
        **Key Insights**:
        - Identify which channels are growing or shrinking in usage.
        - Understand monthly patterns for each channel.
        - Compare channel volumes side-by-side.
        
        **Chart Explanation**: A grouped bar chart showing the number of tickets for each channel, for each month. The table above the chart provides the raw numbers, including a grand total for each month.
        """
    )

    if len(filtered_df) > 0 and COL_CHANNEL in filtered_df.columns and COL_YEAR_MONTH in filtered_df.columns:
        # Check channel distribution in current filtered data
        channel_counts = filtered_df[COL_CHANNEL].value_counts()
        
        # Show debug info for key channels
        key_channels = ['Auto-Generated Event', 'Support Team', 'Walk-in', 'Email', 'Phone']
        channel_info = []
        for ch in key_channels:
            count = channel_counts.get(ch, 0)
            channel_info.append(f"{ch}: {count}")
        
        st.info(f"📊 **Channel Summary**: {', '.join(channel_info)}")
        
        channel_monthly = filtered_df.dropna(subset=[COL_CHANNEL]).groupby([COL_YEAR_MONTH, COL_CHANNEL]).size().reset_index(name='Tickets')

        if not channel_monthly.empty:
            channel_pivot = channel_monthly.pivot_table(index=COL_CHANNEL, columns=COL_YEAR_MONTH, values='Tickets', fill_value=0)
            channel_pivot = channel_pivot.reindex(sorted(channel_pivot.columns), axis=1)
            
            # Ensure all major channels are included even if they have zero tickets
            all_channels_in_data = filtered_df[COL_CHANNEL].dropna().unique()
            missing_channels_in_pivot = [ch for ch in all_channels_in_data if ch not in channel_pivot.index]
            
            if missing_channels_in_pivot:
                # Add missing channels with zeros
                for missing_ch in missing_channels_in_pivot:
                    channel_pivot.loc[missing_ch] = 0
            
            # Sort channels by total volume (descending)
            channel_pivot['Total'] = channel_pivot.sum(axis=1)
            channel_pivot = channel_pivot.sort_values('Total', ascending=False)
            channel_pivot = channel_pivot.drop('Total', axis=1)

            if not channel_pivot.empty:
                grand_total_row = channel_pivot.sum().rename('Grand Total')
                channel_pivot_with_total = pd.concat([channel_pivot, pd.DataFrame(grand_total_row).T])
            else:
                channel_pivot_with_total = channel_pivot

            st_subheader_with_popover(
                "Ticket Channel Breakdown by Month",
                """
                **Purpose**: Track channel usage trends over time to identify seasonal patterns and adoption changes.
                
                **Table Explanation**: Shows exact ticket counts for each channel by month, with grand totals for trend analysis.
                
                **Key Insights**: Look for growing/declining channels, seasonal patterns, and sudden spikes that may indicate issues or process changes.
                """
            )
            st.dataframe(channel_pivot_with_total.style.format("{:.0f}"))

            chart_data_melted = channel_pivot_with_total.reset_index().rename(columns={'index': COL_CHANNEL}).melt(id_vars=COL_CHANNEL, var_name=COL_YEAR_MONTH, value_name='Tickets')

            fig_channel_breakdown = px.bar(chart_data_melted, 
                                           x=COL_YEAR_MONTH, 
                                           y='Tickets', 
                                           color=COL_CHANNEL,
                                           title='Monthly Ticket Volume by Channel',
                                           labels={'Tickets': 'Number of Tickets', COL_YEAR_MONTH: 'Month'},
                                           barmode='group')
            fig_channel_breakdown.update_xaxes(tickangle=45)
            st.plotly_chart(fig_channel_breakdown, use_container_width=True)
        else:
            st.info("No ticket data available for the selected filters to create a channel breakdown.")
    else:
        st.info("No data available to display channel breakdown. Check if 'Channel' column exists and data is loaded.")
    
    st.markdown("---")

    st_header_with_popover(
        "Channel and Location Distribution",
        """
        **Purpose**: Understand how users submit tickets and where issues originate to optimize support channels and regional resources.
        
        **Key Insights**:
        - Preferred communication channels
        - Geographic distribution of issues
        - Channel-specific resolution patterns
        """
    )
    col1, col2 = st.columns(2)
    with col1:
        st_subheader_with_popover(
            "Channel Usage Summary",
            """
            **Purpose**: Show how users prefer to submit tickets.
            **Table Explanation**: Detailed breakdown of ticket submission channels with counts and percentages. Identify most popular submission methods.
            """
        )
        channel_dist = filtered_df.groupby(COL_CHANNEL).size().reset_index(name="Tickets")
        channel_dist["Percentage"] = (channel_dist["Tickets"] / channel_dist["Tickets"].sum() * 100).round(1)
        channel_dist = channel_dist.sort_values("Tickets", ascending=False)
        st.dataframe(channel_dist, use_container_width=True)
    with col2:
        st_subheader_with_popover(
            "Top 10 Locations by Volume",
            """
            **Purpose**: Identify geographic hotspots requiring more support resources.
            **Graph Explanation**: Bar chart of top 10 locations by ticket count. Helps identify sites needing additional IT support or infrastructure improvements.
            """
        )
        location_dist = filtered_df.groupby(COL_LOCATION).size().reset_index(name="Tickets").nlargest(10, 'Tickets')
        fig6 = px.bar(location_dist, x=COL_LOCATION, y="Tickets",
                      title="Top 10 Locations by Ticket Volume")
        fig6.update_xaxes(tickangle=45)
        st.plotly_chart(fig6, use_container_width=True)

    st_header_with_popover(
        "Ticket State Analysis",
        """
        **Purpose**: Monitor ticket lifecycle and identify potential process bottlenecks or workflow issues.
        
        **Key Insights**:
        - Workflow distribution analysis
        - Process bottleneck identification
        - Closure rate monitoring
        """
    )
    state_summary = filtered_df.groupby(COL_STATE).size().reset_index(name="Count")
    if state_summary["Count"].sum() > 0:
        state_summary["Percentage"] = (state_summary["Count"] / state_summary["Count"].sum() * 100).round(1)
    else:
        state_summary["Percentage"] = 0.0
        
    col1, col2 = st.columns(2)
    with col1:
        st_subheader_with_popover(
            "Distribution by State",
            """
            **Purpose**: Monitor ticket lifecycle stages and identify potential bottlenecks.
            **Graph Explanation**: Pie chart showing percentage of tickets in each workflow state. Large "Work In Progress" slice may indicate bottlenecks.
            """
        )
        fig9 = px.pie(state_summary, names=COL_STATE, values="Count",
                      title="Ticket Distribution by State")
        st.plotly_chart(fig9, use_container_width=True)
    with col2:
        st_subheader_with_popover(
            "Ticket State Summary",
            """
            **Purpose**: Detailed breakdown of ticket states with counts and percentages.
            **Table Explanation**: Shows exact numbers and percentages for each workflow state. Use to identify process bottlenecks or closure rates.
            """
        )
        st.dataframe(state_summary, use_container_width=True)

    st_header_with_popover(
        "Categorization Analysis",
        """
        **Purpose**: Identify the most common types of issues to focus improvement efforts and knowledge base development.
        
        **Key Insights**:
        - Common problem patterns
        - Knowledge management opportunities
        - Process improvement focus areas
        """
    )
    st_subheader_with_popover(
        "Top 15 Categories by Volume",
        """
        **Purpose**: Identify most common issue types to focus improvement efforts.
        **Graph Explanation**: Bar chart of top 15 ticket categories by volume. Helps prioritize knowledge base articles, process improvements, and self-service solutions.
        """
    )
            
    cat_summary = filtered_df.groupby(COL_CATEGORIZATION).size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)
    fig10 = px.bar(cat_summary.head(15), x=COL_CATEGORIZATION, y="Tickets",
                   title="Top 15 Categories by Volume",
                   text_auto=True)
    fig10.update_xaxes(tickangle=45)
    st.plotly_chart(fig10, use_container_width=True)
    
    # Add description pattern analysis
    analyze_description_patterns(filtered_df)
    
    # Add service category insights
    add_service_category_insights(filtered_df)

    # Task Type Analysis (Enhanced with TCD data)
    if COL_TASK_TYPE in filtered_df.columns:
        st_header_with_popover(
            "Task Type Classification Analysis",
            """
            **Purpose**: Analyze the distribution of different work types to understand workload composition.
            
            **Task Types**:
            - **INCIDENT**: Unplanned service disruptions requiring resolution
            - **REQUEST**: Planned service requests from users
            - **ENH (Enhancement)**: System improvements and feature additions
            
            **Business Value**:
            - Workload planning and resource allocation
            - Separate SLA tracking for incidents vs service requests
            - Enhancement project tracking and prioritization
            - Capacity planning for different work types
            """
        )
        
        # Calculate task type distribution
        task_type_summary = (
            filtered_df.groupby(COL_TASK_TYPE)
            .agg(
                Count=(COL_NUMBER, "count"),
                Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
                SLA_Compliance=(COL_SLA_MET, "mean")
            )
            .reset_index()
            .sort_values("Count", ascending=False)
        )
        
        # Filter out invalid task types
        task_type_summary = task_type_summary[
            (~task_type_summary[COL_TASK_TYPE].isin(['FALSE', 'TRUE', ''])) & 
            (task_type_summary[COL_TASK_TYPE].notna())
        ]
        
        if len(task_type_summary) > 0:
            # Add percentage calculation
            task_type_summary = task_type_summary.copy()  # Create explicit copy to avoid warnings
            total_valid_tickets = task_type_summary["Count"].sum()
            task_type_summary["Percentage"] = (task_type_summary["Count"] / total_valid_tickets * 100).round(1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st_subheader_with_popover(
                "Task Type Distribution",
                """
                **Purpose**: Understand workload composition for resource planning and SLA management.
                
                **Graph Explanation**: Pie chart showing percentage breakdown of work types. Different task types may have different SLA targets and resource requirements.
                
                **Strategic Value**: Balanced distribution indicates healthy IT operations; skewed distribution may indicate process or infrastructure issues.
                """
            )
                fig_task_dist = px.pie(
                    task_type_summary, 
                    names=COL_TASK_TYPE, 
                    values="Count",
                    title="Work Distribution by Task Type"
                )
                st.plotly_chart(fig_task_dist, use_container_width=True)
            
            with col2:
                st_subheader_with_popover(
                "Task Type Performance",
                """
                **Purpose**: Compare SLA compliance across different work types for targeted improvements.
                
                **Graph Explanation**: Bar chart showing SLA compliance rate by task type. Color coding (green to red) indicates performance level.
                
                **Key Insights**: Lower compliance rates may indicate need for specialized skills, tools, or process improvements for specific work types.
                """
            )
                fig_task_perf = px.bar(
                    task_type_summary, 
                    x=COL_TASK_TYPE, 
                    y="SLA_Compliance",
                    title="SLA Compliance by Task Type",
                    text=task_type_summary["SLA_Compliance"].map("{:.1%}".format),
                    color="SLA_Compliance",
                    color_continuous_scale="RdYlGn"
                )
                fig_task_perf.update_layout(yaxis_tickformat=".0%")
                fig_task_perf.update_traces(textposition="outside")
                st.plotly_chart(fig_task_perf, use_container_width=True)
            
            st_subheader_with_popover(
                "Detailed Task Type Analysis",
                """
                **Purpose**: Comprehensive task type metrics for capacity planning and performance management.
                
                **Business Applications**:
                - **Capacity Planning**: Use count and percentage for staffing decisions
                - **SLA Management**: Track separate performance targets by work type
                - **Process Improvement**: Focus on task types with poor performance
                - **Resource Allocation**: Balance teams based on workload distribution
                """
            )
            display_cols = [COL_TASK_TYPE, "Count", "Percentage", "Avg_Resolution_Hours", "SLA_Compliance"]
            task_display = task_type_summary[display_cols].copy()
            if 'SLA_Compliance' in task_display.columns:
                task_display['SLA_Compliance'] = task_display['SLA_Compliance'].map('{:.1%}'.format)
            task_display = task_display.round(2)
            st.dataframe(task_display, use_container_width=True)
            
            # Insights based on actual data
            incident_count = task_type_summary[task_type_summary[COL_TASK_TYPE] == "INCIDENT"]["Count"].sum()
            request_count = task_type_summary[task_type_summary[COL_TASK_TYPE] == "REQUEST"]["Count"].sum()
            
            st.info(f"📊 **Workload Composition**: {incident_count:,} incidents vs {request_count:,} service requests - useful for separate SLA tracking")
            
            # Task Type Strategic Insights
            if len(task_type_summary) > 0:
                st.write("#### Task Type Strategic Insights")
                
                # Workload balance analysis
                incident_pct = (incident_count / total_valid_tickets * 100) if total_valid_tickets > 0 else 0
                request_pct = (request_count / total_valid_tickets * 100) if total_valid_tickets > 0 else 0
                
                col1, col2 = st.columns(2)
                with col1:
                    if incident_pct > 70:
                        st.warning(f"⚠️ **High Incident Load**: {incident_pct:.1f}% incidents - may indicate infrastructure issues")
                    elif incident_pct < 30:
                        st.info(f"✅ **Stable Environment**: {incident_pct:.1f}% incidents - good operational health")
                    else:
                        st.info(f"📊 **Balanced Load**: {incident_pct:.1f}% incidents vs {request_pct:.1f}% requests")
                
                with col2:
                    # SLA performance by task type
                    incident_sla = task_type_summary[task_type_summary[COL_TASK_TYPE] == "INCIDENT"]["SLA_Compliance"]
                    request_sla = task_type_summary[task_type_summary[COL_TASK_TYPE] == "REQUEST"]["SLA_Compliance"]
                    
                    if len(incident_sla) > 0 and len(request_sla) > 0:
                        if incident_sla.iloc[0] < request_sla.iloc[0] - 0.1:
                            st.warning("⚠️ **Incident SLA Gap**: Incidents underperforming vs requests - check resolution processes")
                        elif request_sla.iloc[0] < incident_sla.iloc[0] - 0.1:
                            st.info("📊 **Request Optimization**: Service requests may need process streamlining")
                        else:
                            st.success("✅ **Balanced Performance**: Similar SLA performance across task types")
        else:
            st.info("No valid task type data available for analysis")
    else:
        st.info("Task type analysis not available - requires Task Type column in data")

    # Channel Efficiency Analysis
    st_header_with_popover(
        "Channel Efficiency Analysis",
        """
        **Purpose**: Optimize service desk operations by analyzing efficiency across different contact channels.
        
        **Channel Distribution**:
        - **Auto-Generated Event**: 45% of tickets (5,960) - Automated monitoring alerts
        - **Email**: 45% of tickets (5,915) - Primary user contact method  
        - **Phone**: 3% of tickets (449) - High-touch support channel
        - **Self-service**: 2% of tickets (241) - User self-resolution
        - **Other Channels**: 5% (Walk-in, Chat, etc.)
        
        **Key Insights**:
        - Channel resolution efficiency for resource optimization
        - First-contact resolution rates by channel
        - Channel preference impact on SLA performance
        - Self-service adoption opportunities
        """
    )
    
    # Calculate channel efficiency metrics
    if COL_CHANNEL in filtered_df.columns:
        channel_efficiency = (
            filtered_df.groupby(COL_CHANNEL)
            .agg(
                Tickets=(COL_NUMBER, "count"),
                Avg_Resolution_Hours=(COL_RESOLUTION_HOURS, "mean"),
                SLA_Compliance=(COL_SLA_MET, "mean"),
                P1_Count=(COL_PRIORITY_NUMERIC, lambda x: (x == 1).sum()),
                P2_Count=(COL_PRIORITY_NUMERIC, lambda x: (x == 2).sum())
            )
            .reset_index()
            .sort_values("Tickets", ascending=False)
        )
        
        # Filter valid channels and add percentage
        channel_efficiency = channel_efficiency[
            (channel_efficiency[COL_CHANNEL].notna()) & 
            (channel_efficiency[COL_CHANNEL] != "")
        ]
        
        if len(channel_efficiency) > 0:
            channel_efficiency = channel_efficiency.copy()  # Create explicit copy to avoid warnings
            total_channel_tickets = channel_efficiency["Tickets"].sum()
            channel_efficiency["Percentage"] = (channel_efficiency["Tickets"] / total_channel_tickets * 100).round(1)
            
            # Categorize channels for analysis
            automated_channels = ["Auto-Generated Event"]
            human_channels = ["Email", "Phone", "Walk-in", "Instant Messaging/Chat"]
            self_service_channels = ["Self-service"]
            
            channel_efficiency["Channel_Type"] = channel_efficiency[COL_CHANNEL].apply(
                lambda x: "Automated" if x in automated_channels
                else "Self-Service" if x in self_service_channels
                else "Human-Assisted" if x in human_channels
                else "Other"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                st_subheader_with_popover(
                    "Channel Volume Distribution",
                    """
                    **Purpose**: Understand how users prefer to submit tickets for channel optimization.
                    
                    **Channel Types**:
                    - **Auto-Generated**: Automated monitoring alerts (usually infrastructure)
                    - **Email**: Primary user contact method
                    - **Phone**: High-touch support channel
                    - **Self-service**: User self-resolution portal
                    
                    **Strategic Value**: Larger slices indicate higher usage channels requiring optimization.
                    """
                )
                top_channels = channel_efficiency.head(8)
                fig_channel_vol = px.pie(
                    top_channels,
                    names=COL_CHANNEL,
                    values="Tickets",
                    title="Channel Volume Distribution"
                )
                st.plotly_chart(fig_channel_vol, use_container_width=True)
            
            with col2:
                st_subheader_with_popover(
                    "Channel Efficiency Comparison",
                    """
                    **Purpose**: Compare channel performance to optimize service desk operations.
                    
                    **Chart Explanation**: Bubble scatter plot where:
                    - **X-axis**: Average resolution time (lower = better)
                    - **Y-axis**: SLA compliance rate (higher = better)
                    - **Bubble size**: Ticket volume (larger = more tickets)
                    - **Color**: Channel type classification
                    
                    **Optimal Quadrant**: Top-left (high compliance + fast resolution)
                    """
                )
                fig_channel_eff = px.scatter(
                    channel_efficiency.head(8),
                    x="Avg_Resolution_Hours",
                    y="SLA_Compliance", 
                    size="Tickets",
                    hover_name=COL_CHANNEL,
                    title="Channel Efficiency: Resolution Time vs SLA Compliance",
                    labels={
                        "Avg_Resolution_Hours": "Average Resolution Hours",
                        "SLA_Compliance": "SLA Compliance Rate"
                    },
                    color="Channel_Type",
                    color_discrete_map={
                        "Automated": "#2ecc71",
                        "Self-Service": "#3498db", 
                        "Human-Assisted": "#e74c3c",
                        "Other": "#95a5a6"
                    }
                )
                fig_channel_eff.update_layout(yaxis_tickformat=".0%")
                st.plotly_chart(fig_channel_eff, use_container_width=True)
            
            # Channel type performance summary
            st_subheader_with_popover(
                "Channel Type Performance Summary",
                """
                **Purpose**: Aggregated performance metrics by channel category for strategic planning.
                
                **Channel Categories**:
                - **Automated**: System-generated alerts (monitoring, alerts)
                - **Human-Assisted**: Requires staff interaction (phone, email, chat)
                - **Self-Service**: User self-resolution capabilities
                - **Other**: Specialized or miscellaneous channels
                
                **Key Metrics**: Total volume, average resolution time, SLA compliance, channel count
                """
            )
            channel_type_summary = (
                channel_efficiency.groupby("Channel_Type")
                .agg(
                    Total_Tickets=("Tickets", "sum"),
                    Avg_Resolution_Hours=("Avg_Resolution_Hours", "mean"),
                    Avg_SLA_Compliance=("SLA_Compliance", "mean"),
                    Channels=("Channel_Type", "count")
                )
                .reset_index()
                .round(2)
            )
            st.dataframe(channel_type_summary, use_container_width=True)
            
            # Channel insights and recommendations
            auto_generated = channel_efficiency[channel_efficiency[COL_CHANNEL] == "Auto-Generated Event"]
            email_channel = channel_efficiency[channel_efficiency[COL_CHANNEL] == "Email"]
            self_service = channel_efficiency[channel_efficiency[COL_CHANNEL] == "Self-service"]
            
            if len(auto_generated) > 0 and len(email_channel) > 0:
                auto_sla = auto_generated.iloc[0]["SLA_Compliance"]
                email_sla = email_channel.iloc[0]["SLA_Compliance"]
                
                st.write("#### Channel Optimization Insights")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if len(auto_generated) > 0:
                        auto_tickets = auto_generated.iloc[0]["Tickets"]
                        st.metric("Auto-Generated Events", f"{auto_tickets:,}", 
                                f"{auto_sla:.1%} SLA")
                
                with col2:
                    if len(email_channel) > 0:
                        email_tickets = email_channel.iloc[0]["Tickets"]
                        st.metric("Email Channel", f"{email_tickets:,}", 
                                f"{email_sla:.1%} SLA")
                
                with col3:
                    if len(self_service) > 0:
                        ss_tickets = self_service.iloc[0]["Tickets"]
                        ss_sla = self_service.iloc[0]["SLA_Compliance"]
                        st.metric("Self-Service", f"{ss_tickets:,}", 
                                f"{ss_sla:.1%} SLA")
                
                # Provide optimization recommendations
                if auto_sla > email_sla:
                    st.info("💡 **Insight**: Auto-generated events have higher SLA compliance - consider automation opportunities")
                else:
                    st.info("💡 **Insight**: Human channels outperforming automation - review auto-generated event handling")
                
                if len(self_service) > 0:
                    ss_percentage = (self_service.iloc[0]["Tickets"] / total_channel_tickets * 100)
                    if ss_percentage < 5:
                        st.warning("📈 **Opportunity**: Self-service adoption is low - consider improving self-service capabilities")
                
                # Additional channel efficiency insights
                st.write("#### Channel Efficiency Recommendations")
                phone_channel = channel_efficiency[channel_efficiency[COL_CHANNEL] == "Phone"]
                if len(phone_channel) > 0:
                    phone_res_time = phone_channel.iloc[0]["Avg_Resolution_Hours"]
                    email_res_time = email_channel.iloc[0]["Avg_Resolution_Hours"] if len(email_channel) > 0 else 0
                    
                    if phone_res_time > email_res_time * 1.5:
                        st.info("💡 **Insight**: Phone channel has longer resolution times - consider phone triage or escalation process")
                
                # Volume-based recommendations
                total_volume = channel_efficiency["Tickets"].sum()
                high_volume_channels = channel_efficiency[channel_efficiency["Tickets"] > total_volume * 0.1]
                
                if len(high_volume_channels) > 0:
                    low_sla_channels = high_volume_channels[high_volume_channels["SLA_Compliance"] < 0.85]
                    if len(low_sla_channels) > 0:
                        problematic_channels = ", ".join(low_sla_channels[COL_CHANNEL].tolist())
                        st.warning(f"⚠️ **Priority Action**: High-volume channels with poor SLA: {problematic_channels}")
            
            st_subheader_with_popover(
                "Detailed Channel Performance",
                """
                **Purpose**: Granular channel analysis for operational optimization and resource allocation.
                
                **Use Cases**:
                - Identify most efficient channels for user education
                - Allocate staff resources based on channel demand
                - Improve underperforming channels
                - Track self-service adoption rates
                
                **Key Insight**: Channels with high volume but low efficiency may need process improvements.
                """
            )
            channel_display_cols = [COL_CHANNEL, "Channel_Type", "Tickets", "Percentage", 
                                  "Avg_Resolution_Hours", "SLA_Compliance"]
            channel_display = channel_efficiency[channel_display_cols].head(10).copy()
            if 'SLA_Compliance' in channel_display.columns:
                channel_display['SLA_Compliance'] = channel_display['SLA_Compliance'].map('{:.1%}'.format)
            channel_display = channel_display.round(2)
            st.dataframe(channel_display, use_container_width=True)
            
            # Add box plot for resolution time distribution by channel
            st_subheader_with_popover(
                "Resolution Time Distribution by Channel",
                """
                **Purpose**: Analyze resolution time variability across different submission channels.
                
                **Box Plot Elements**:
                - **Center Line**: Median resolution time (50th percentile)
                - **Box**: Interquartile range (25th to 75th percentile)
                - **Whiskers**: 1.5x IQR or min/max values
                - **Dots**: Outliers beyond whisker range
                
                **Key Insights**:
                - **Narrow boxes**: Consistent resolution times
                - **Wide boxes**: High variability in resolution times
                - **Many outliers**: Process inconsistencies or complex cases
                - **Compare medians**: True center performance across channels
                """
            )
            
            # Filter data for box plot (remove extreme outliers for better visualization)
            top_channels_for_plot = channel_efficiency.head(6)[COL_CHANNEL].tolist()
            channel_plot_data = filtered_df[
                (filtered_df[COL_CHANNEL].isin(top_channels_for_plot)) & 
                (filtered_df[COL_RESOLUTION_HOURS] <= filtered_df[COL_RESOLUTION_HOURS].quantile(0.95)) &
                (filtered_df[COL_RESOLUTION_HOURS].notna())
            ]
            
            if len(channel_plot_data) > 0:
                fig_channel_box = px.box(
                    channel_plot_data,
                    x=COL_CHANNEL,
                    y=COL_RESOLUTION_HOURS,
                    title="Resolution Time Distribution by Top 6 Channels",
                    labels={
                        COL_RESOLUTION_HOURS: "Resolution Time (Hours)",
                        COL_CHANNEL: "Submission Channel"
                    },
                    color=COL_CHANNEL
                )
                fig_channel_box.update_xaxes(tickangle=45)
                fig_channel_box.update_layout(height=500)
                st.plotly_chart(fig_channel_box, use_container_width=True)
                
                # Channel distribution insights based on box plot
                st.write("#### Channel Distribution Insights")
                
                channel_stats = []
                for channel in top_channels_for_plot:
                    channel_data = channel_plot_data[channel_plot_data[COL_CHANNEL] == channel][COL_RESOLUTION_HOURS]
                    if len(channel_data) >= 5:  # Need enough data for meaningful stats
                        median_time = channel_data.median()
                        q1 = channel_data.quantile(0.25)
                        q3 = channel_data.quantile(0.75)
                        iqr = q3 - q1
                        # Calculate coefficient of variation for consistency
                        mean_time = channel_data.mean()
                        std_time = channel_data.std()
                        
                        # Consistency score based on coefficient of variation (lower CV = more consistent)
                        cv = (std_time / mean_time) if mean_time > 0 else 0
                        consistency_score = max(0, 100 - (cv * 100))  # Cap at 0% minimum
                        
                        # Alternative: IQR-based consistency (capped at reasonable bounds)
                        iqr_ratio = (iqr / median_time) if median_time > 0 else 0
                        iqr_consistency = max(0, min(100, 100 - (iqr_ratio * 50)))  # Scale down and cap
                        
                        channel_stats.append({
                            'Channel': channel,
                            'Median_Hours': median_time,
                            'Mean_Hours': mean_time,
                            'IQR_Hours': iqr,
                            'Std_Hours': std_time,
                            'CV_Ratio': cv,
                            'Consistency_Score': consistency_score,
                            'IQR_Consistency': iqr_consistency
                        })
                
                if channel_stats:
                    stats_df = pd.DataFrame(channel_stats)
                    
                    # Find most/least consistent channels
                    most_consistent = stats_df.loc[stats_df['Consistency_Score'].idxmax()]
                    least_consistent = stats_df.loc[stats_df['Consistency_Score'].idxmin()]
                    fastest_median = stats_df.loc[stats_df['Median_Hours'].idxmin()]
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.success(f"🎯 **Most Consistent**: {most_consistent['Channel']} (median: {most_consistent['Median_Hours']:.1f}h, CV: {most_consistent['CV_Ratio']:.2f})")
                    
                    with col2:
                        st.info(f"⚡ **Fastest Median**: {fastest_median['Channel']} ({fastest_median['Median_Hours']:.1f}h median, {fastest_median['Mean_Hours']:.1f}h avg)")
                    
                    with col3:
                        if least_consistent['Consistency_Score'] < 50:
                            cv_ratio = least_consistent['CV_Ratio']
                            st.warning(f"📊 **Variable Performance**: {least_consistent['Channel']} (CV: {cv_ratio:.1f}, consistency: {least_consistent['Consistency_Score']:.0f}%) - high variability")
                        elif least_consistent['Consistency_Score'] < 70:
                            st.info(f"📊 **Moderate Variability**: {least_consistent['Channel']} (consistency: {least_consistent['Consistency_Score']:.0f}%)")
                        else:
                            st.success(f"📊 **Good Consistency**: All channels show good consistency (lowest: {least_consistent['Consistency_Score']:.0f}%)")
            else:
                st.info("Insufficient data for resolution time distribution analysis")
        else:
            st.info("No valid channel data available for efficiency analysis")
    else:
        st.info("Channel efficiency analysis not available - requires Channel column in data")

# --- Additional Insights Helper Functions -----------------------------

def analyze_description_patterns(filtered_df):
    """Analyze short descriptions against resolution times to identify patterns."""
    if COL_SHORT_DESC in filtered_df.columns and len(filtered_df) > 0:
        # Create a copy for analysis
        desc_analysis = filtered_df[[COL_SHORT_DESC, COL_RESOLUTION_HOURS, COL_PRIORITY, COL_SLA_MET]].copy()
        desc_analysis = desc_analysis.dropna(subset=[COL_SHORT_DESC])
        
        if len(desc_analysis) == 0:
            return
        
        st_header_with_popover(
            "Short Description Resolution Analysis",
            """
            **Purpose**: Analyze ticket resolution patterns based on short description keywords to identify process improvement opportunities.
            
            **Analysis Methods**:
            - **Keyword Pattern Recognition**: Common terms in slow/fast resolving tickets
            - **Request Type Classification**: Service requests vs incidents vs enhancements
            - **Complexity Indicators**: Keywords that predict longer resolution times
            - **Process Optimization**: Identify description patterns for automation or self-service
            
            **Business Value**: Enable predictive routing, better SLA estimation, and process improvements.
            """
        )
        
        # Analyze by common keywords and prefixes
        keyword_analysis = []
        
        # Define keyword patterns to analyze
        import re
        keywords = {
            'Service Request': ['*Service Request', 'Service Request:', '*SR'],
            'Enhancement': ['*ENH', 'Enhancement', 'ENH:'],
            'Issue': ['Issue:', 'Problem:', 'Error:'],
            'Access Request': ['access', 'Access', 'permission', 'Permission'],
            'SAP Related': ['SAP', 'S/4HANA', 'SuccessFactors'],
            'Network/Infrastructure': ['Network', 'internet', 'connection', 'VPN', 'firewall'],
            'Hardware/Equipment': ['laptop', 'hardware', 'equipment', 'device', 'computer'],
            'Software/Application': ['application', 'software', 'app', 'system'],
            'Password/Login': ['password', 'login', 'authentication', 'account'],
            'Email/Communication': ['email', 'outlook', 'communication', 'phone']
        }
        
        for category, terms in keywords.items():
            # Find tickets containing any of these terms (case insensitive, escape special chars)
            escaped_terms = [re.escape(term) for term in terms]
            pattern = '|'.join(escaped_terms)
            mask = desc_analysis[COL_SHORT_DESC].str.contains(pattern, case=False, na=False)
            matching_tickets = desc_analysis[mask]
            
            if len(matching_tickets) >= 5:  # Only analyze categories with enough data
                avg_resolution = matching_tickets[COL_RESOLUTION_HOURS].mean()
                sla_compliance = matching_tickets[COL_SLA_MET].mean()
                ticket_count = len(matching_tickets)
                median_resolution = matching_tickets[COL_RESOLUTION_HOURS].median()
                
                keyword_analysis.append({
                    'Category': category,
                    'Tickets': ticket_count,
                    'Avg_Resolution_Hours': avg_resolution,
                    'Median_Resolution_Hours': median_resolution,
                    'SLA_Compliance': sla_compliance,
                    'Percentage': (ticket_count / len(desc_analysis) * 100)
                })
        
        if keyword_analysis:
            keyword_df = pd.DataFrame(keyword_analysis)
            keyword_df = keyword_df.sort_values('Avg_Resolution_Hours', ascending=False)
            
            # Display results
            col1, col2 = st.columns(2)
            
            with col1:
                st_subheader_with_popover(
                    "Resolution Time by Description Type",
                    """
                    **Purpose**: Identify which types of requests take longest to resolve.
                    
                    **Chart Explanation**: Bar chart showing average resolution time by description category. Longer bars indicate request types that take more time to resolve.
                    
                    **Key Insights**: Use this to prioritize automation, self-service options, or process improvements for slow-resolving categories.
                    """
                )
                fig_desc_time = px.bar(
                    keyword_df,
                    x='Avg_Resolution_Hours',
                    y='Category',
                    title='Average Resolution Time by Description Type',
                    text=keyword_df['Avg_Resolution_Hours'].round(1),
                    color='SLA_Compliance',
                    color_continuous_scale='RdYlGn',
                    labels={'Avg_Resolution_Hours': 'Average Resolution Hours'}
                )
                fig_desc_time.update_traces(textposition='outside')
                fig_desc_time.update_layout(height=400)
                st.plotly_chart(fig_desc_time, use_container_width=True)
            
            with col2:
                st_subheader_with_popover(
                    "Volume vs Performance Analysis",
                    """
                    **Purpose**: Compare ticket volume against SLA performance for different description types.
                    
                    **Chart Explanation**: Bubble scatter plot where:
                    - X-axis: Average resolution time (lower = better)
                    - Y-axis: SLA compliance rate (higher = better)
                    - Bubble size: Ticket volume (larger = more tickets)
                    
                    **Optimal Quadrant**: Top-left (high SLA compliance + fast resolution)
                    """
                )
                fig_desc_perf = px.scatter(
                    keyword_df,
                    x='Avg_Resolution_Hours',
                    y='SLA_Compliance',
                    size='Tickets',
                    hover_name='Category',
                    title='Description Type Performance Analysis',
                    labels={
                        'Avg_Resolution_Hours': 'Average Resolution Hours',
                        'SLA_Compliance': 'SLA Compliance Rate'
                    },
                    color='Tickets',
                    color_continuous_scale='Blues'
                )
                fig_desc_perf.update_layout(yaxis_tickformat='.0%')
                st.plotly_chart(fig_desc_perf, use_container_width=True)
            
            # Detailed analysis table
            st_subheader_with_popover(
                "Detailed Description Analysis",
                """
                **Purpose**: Comprehensive breakdown of resolution patterns by description type.
                
                **Key Metrics**:
                - **Tickets**: Volume of tickets in this category
                - **Percentage**: Share of total tickets
                - **Avg_Resolution_Hours**: Mean time to resolve
                - **Median_Resolution_Hours**: Middle value (less affected by outliers)
                - **SLA_Compliance**: Percentage meeting SLA targets
                
                **Use Cases**: Identify automation candidates, process improvements, and resource allocation priorities.
                """
            )
            display_cols = ['Category', 'Tickets', 'Percentage', 'Avg_Resolution_Hours', 'Median_Resolution_Hours', 'SLA_Compliance']
            keyword_display = keyword_df[display_cols].copy()
            if 'SLA_Compliance' in keyword_display.columns:
                keyword_display['SLA_Compliance'] = keyword_display['SLA_Compliance'].map('{:.1%}'.format)
            keyword_display = keyword_display.round(2)
            st.dataframe(keyword_display, use_container_width=True)
            
            # Additional visualization for better category comparison
            st_subheader_with_popover(
                "Category Performance Comparison Charts",
                """
                **Purpose**: Visual comparison of description categories across multiple performance dimensions.
                
                **Chart Types**:
                - **Dual-Axis Chart**: Volume vs Average Resolution Time
                - **Resolution Time Variability**: Compare average vs median resolution times
                - **Performance Matrix**: Volume vs SLA Compliance
                
                **Key Insights**: Identify categories that are high-volume but poor-performing, or low-volume but problematic.
                """
            )
            
            # Chart 1: Dual-axis chart showing Volume vs Resolution Time
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("##### Volume vs Resolution Time")
                
                # Create a dual-axis chart using secondary_y
                fig_dual = go.Figure()
                
                # Add bar chart for ticket volume
                fig_dual.add_trace(
                    go.Bar(
                        x=keyword_df['Category'],
                        y=keyword_df['Tickets'],
                        name='Ticket Volume',
                        yaxis='y1',
                        marker_color='lightblue',
                        opacity=0.7
                    )
                )
                
                # Add line chart for average resolution time
                fig_dual.add_trace(
                    go.Scatter(
                        x=keyword_df['Category'],
                        y=keyword_df['Avg_Resolution_Hours'],
                        mode='lines+markers',
                        name='Avg Resolution Time (h)',
                        yaxis='y2',
                        line=dict(color='red', width=3),
                        marker=dict(size=8)
                    )
                )
                
                # Update layout for dual axis
                fig_dual.update_layout(
                    title='Volume vs Resolution Time by Category',
                    xaxis=dict(title='Category', tickangle=45),
                    yaxis=dict(
                        title='Ticket Volume',
                        side='left',
                        color='blue'
                    ),
                    yaxis2=dict(
                        title='Average Resolution Time (Hours)',
                        side='right',
                        overlaying='y',
                        color='red'
                    ),
                    height=500,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_dual, use_container_width=True)
            
            with col2:
                st.write("##### Resolution Time Variability")
                
                # Chart showing Average vs Median resolution times
                fig_variability = go.Figure()
                
                # Add average resolution time bars
                fig_variability.add_trace(
                    go.Bar(
                        x=keyword_df['Category'],
                        y=keyword_df['Avg_Resolution_Hours'],
                        name='Average Resolution Time',
                        marker_color='orange',
                        opacity=0.7
                    )
                )
                
                # Add median resolution time as line
                fig_variability.add_trace(
                    go.Scatter(
                        x=keyword_df['Category'],
                        y=keyword_df['Median_Resolution_Hours'],
                        mode='lines+markers',
                        name='Median Resolution Time',
                        line=dict(color='green', width=3),
                        marker=dict(size=8, color='green')
                    )
                )
                
                fig_variability.update_layout(
                    title='Average vs Median Resolution Time',
                    xaxis=dict(title='Category', tickangle=45),
                    yaxis=dict(title='Resolution Time (Hours)'),
                    height=500,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_variability, use_container_width=True)
            
            # Chart 2: Performance Matrix (Volume vs SLA Compliance)
            st.write("##### Performance Matrix: Volume vs SLA Compliance")
            
            fig_matrix = px.scatter(
                keyword_df,
                x='Tickets',
                y='SLA_Compliance',
                size='Avg_Resolution_Hours',
                hover_name='Category',
                title='Category Performance Matrix',
                labels={
                    'Tickets': 'Ticket Volume',
                    'SLA_Compliance': 'SLA Compliance Rate',
                    'Avg_Resolution_Hours': 'Avg Resolution Time (Hours)'
                },
                color='Avg_Resolution_Hours',
                color_continuous_scale='RdYlGn_r',
                size_max=50
            )
            
            # Add quadrant lines
            max_tickets = keyword_df['Tickets'].max()
            fig_matrix.add_hline(y=0.85, line_dash="dash", line_color="red", 
                               annotation_text="85% SLA Threshold")
            fig_matrix.add_vline(x=max_tickets * 0.2, line_dash="dash", line_color="orange",
                               annotation_text="High Volume Threshold")
            
            fig_matrix.update_layout(
                yaxis_tickformat='.0%',
                height=600,
                annotations=[
                    dict(x=max_tickets * 0.7, y=0.95, text="High Volume<br>High Performance", 
                         showarrow=False, bgcolor="lightgreen", opacity=0.7),
                    dict(x=max_tickets * 0.7, y=0.75, text="High Volume<br>Poor Performance", 
                         showarrow=False, bgcolor="lightcoral", opacity=0.7),
                    dict(x=max_tickets * 0.1, y=0.95, text="Low Volume<br>High Performance", 
                         showarrow=False, bgcolor="lightblue", opacity=0.7),
                    dict(x=max_tickets * 0.1, y=0.75, text="Low Volume<br>Poor Performance", 
                         showarrow=False, bgcolor="lightyellow", opacity=0.7)
                ]
            )
            
            st.plotly_chart(fig_matrix, use_container_width=True)
            
            # Chart insights based on the visualizations
            st.write("##### Visual Analysis Insights")
            
            # Find interesting patterns from the charts
            high_volume_low_sla = keyword_df[(keyword_df['Tickets'] > keyword_df['Tickets'].quantile(0.6)) & 
                                            (keyword_df['SLA_Compliance'] < 0.85)]
            high_variability = keyword_df[keyword_df['Avg_Resolution_Hours'] > keyword_df['Median_Resolution_Hours'] * 1.5]
            efficient_categories = keyword_df[(keyword_df['SLA_Compliance'] > 0.90) & 
                                            (keyword_df['Avg_Resolution_Hours'] < keyword_df['Avg_Resolution_Hours'].median())]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if len(high_volume_low_sla) > 0:
                    hvls_list = ", ".join(high_volume_low_sla['Category'].head(2).tolist())
                    st.error(f"🚨 **Priority Focus**: {hvls_list} - high volume with poor SLA (red quadrant)")
                else:
                    st.success("✅ **Volume Performance**: No high-volume categories with poor SLA")
            
            with col2:
                if len(high_variability) > 0:
                    hv_list = ", ".join(high_variability['Category'].head(2).tolist())
                    st.warning(f"📊 **High Variability**: {hv_list} - large gap between average and median times")
                else:
                    st.success("✅ **Consistent Performance**: Low variability across categories")
            
            with col3:
                if len(efficient_categories) > 0:
                    eff_list = ", ".join(efficient_categories['Category'].head(2).tolist())
                    st.success(f"🎆 **Best Practices**: {eff_list} - high SLA with fast resolution")
                else:
                    st.info("📊 **Performance**: No standout efficient categories identified")
            
            # Generate insights
            st.write("#### Description Pattern Insights")
            
            # Find slow categories
            slow_categories = keyword_df[keyword_df['Avg_Resolution_Hours'] > keyword_df['Avg_Resolution_Hours'].quantile(0.75)]
            fast_categories = keyword_df[keyword_df['Avg_Resolution_Hours'] < keyword_df['Avg_Resolution_Hours'].quantile(0.25)]
            high_volume_slow = keyword_df[(keyword_df['Percentage'] > 5) & (keyword_df['SLA_Compliance'] < 0.85)]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if len(slow_categories) > 0:
                    slow_list = ", ".join(slow_categories['Category'].head(3).tolist())
                    avg_slow_time = slow_categories['Avg_Resolution_Hours'].mean()
                    st.warning(f"🐌 **Slow Resolution**: {slow_list} (avg: {avg_slow_time:.1f}h) - consider process optimization")
                else:
                    st.success("✅ **Consistent Performance**: No significantly slow description types identified")
            
            with col2:
                if len(fast_categories) > 0:
                    fast_list = ", ".join(fast_categories['Category'].head(3).tolist())
                    avg_fast_time = fast_categories['Avg_Resolution_Hours'].mean()
                    st.success(f"⚡ **Fast Resolution**: {fast_list} (avg: {avg_fast_time:.1f}h) - good process examples")
                else:
                    st.info("📊 **Balanced Performance**: No standout fast-resolving categories")
            
            with col3:
                if len(high_volume_slow) > 0:
                    priority_list = ", ".join(high_volume_slow['Category'].head(2).tolist())
                    st.error(f"🚨 **Priority Focus**: {priority_list} - high volume with poor SLA performance")
                else:
                    st.success("✅ **Volume Health**: High-volume categories meeting SLA targets")
            
            # Automation recommendations
            service_requests = keyword_df[keyword_df['Category'].str.contains('Service Request|Access Request', na=False)]
            if len(service_requests) > 0:
                sr_volume = service_requests['Percentage'].sum()
                sr_avg_time = service_requests['Avg_Resolution_Hours'].mean()
                if sr_volume > 20:
                    st.info(f"🤖 **Automation Opportunity**: Service/Access requests represent {sr_volume:.1f}% of tickets (avg: {sr_avg_time:.1f}h) - good candidates for self-service portal")
        else:
            st.info("No significant description patterns found for analysis")
    else:
        st.info("Short description analysis not available - requires Short description column in data")

def add_service_category_insights(filtered_df):
    """Add intelligent insights for service category analysis."""
    if COL_CATEGORIZATION in filtered_df.columns:
        cat_summary = filtered_df.groupby(COL_CATEGORIZATION).agg({
            COL_NUMBER: 'count',
            COL_RESOLUTION_HOURS: 'mean',
            COL_SLA_MET: 'mean',
            COL_PRIORITY_NUMERIC: lambda x: (x <= 2).sum()  # P1 and P2 count
        }).reset_index()
        
        cat_summary.columns = [COL_CATEGORIZATION, 'Tickets', 'Avg_Resolution_Hours', 'SLA_Compliance', 'Critical_Count']
        cat_summary = cat_summary.sort_values('Tickets', ascending=False).head(10)
        
        if len(cat_summary) > 0:
            # Find categories needing attention
            poor_sla_cats = cat_summary[cat_summary['SLA_Compliance'] < 0.80]
            high_res_time_cats = cat_summary[cat_summary['Avg_Resolution_Hours'] > cat_summary['Avg_Resolution_Hours'].quantile(0.75)]
            
            # Service Category Performance Insights section removed as requested

# --- Data Quality Tab Helper Functions ---------------------------------

def _check_unresolved_active(df):
    """Checks for active tickets correctly missing a resolution date."""
    unresolved_active = df[df[COL_RESOLVED].isna() & df[COL_STATE].isin([STATE_ACTIVE, STATE_WIP])]
    st_subheader_with_popover(
        f"Active Tickets without Resolution Date: {len(unresolved_active)}",
        "**Purpose**: Identify active tickets missing resolution timestamps. Active/WIP tickets *should not* have resolution dates, so this is expected behavior."
    )
    return 0

def _check_missing_ci(df):
    """Checks for tickets with missing or invalid Configuration Items."""
    missing_ci = df[df[COL_CONFIG_ITEM].isna() | (df[COL_CONFIG_ITEM] == "CI_notfound")]
    st_subheader_with_popover(
        f"Tickets with Missing/Invalid Configuration Items: {len(missing_ci)} ({len(missing_ci)/len(df)*100:.1f}%)",
        "**Purpose**: Track data completeness for the configuration item field. Missing CIs make it harder to identify recurring issues with specific systems."
    )
    return 0 

def _check_unusual_resolution(df):
    """Checks for tickets with unusual resolution times (negative or >365 days)."""
    unusual_resolution = df[(df[COL_RESOLUTION_DAYS] < 0) | (df[COL_RESOLUTION_DAYS] > 365)]
    st_subheader_with_popover(
        f"Unusual Resolution Times: {len(unusual_resolution)}",
        "**Purpose**: Detect data quality issues where resolution time is negative or over a year. This indicates data entry errors or extreme process outliers."
    )
    if len(unusual_resolution) > 0:
        st.warning(f"🚨 Found {len(unusual_resolution)} tickets with unusual resolution times (negative or >365 days)")
        st.dataframe(unusual_resolution[[COL_NUMBER, COL_OPENED, COL_RESOLVED, COL_RESOLUTION_DAYS, COL_STATE]].head(10))
    return len(unusual_resolution)

def _check_resolved_without_opened(df):
    """Checks for tickets that are resolved but have no open date."""
    no_open_but_resolved = df[df[COL_OPENED].isna() & df[COL_RESOLVED].notna()]
    st_subheader_with_popover(
        f"Resolved without an Opening Date: {len(no_open_but_resolved)}",
        "**Purpose**: Identify records with impossible data (resolved without being opened), likely from data import errors."
    )
    if len(no_open_but_resolved) > 0:
        st.error(f"🚨 Found {len(no_open_but_resolved)} tickets with resolution date but no opening date")
        st.dataframe(no_open_but_resolved[[COL_NUMBER, COL_OPENED, COL_RESOLVED, COL_STATE, COL_SHORT_DESC]].head(10))
    else:
        st.success("✅ No tickets found with resolution date but missing opening date")
    return len(no_open_but_resolved)

def _check_closed_without_resolution(df):
    """Checks for closed tickets that are missing a resolution date."""
    closed_no_resolution = df[(df[COL_STATE].isin(CLOSED_STATES)) & (df[COL_RESOLVED].isna())]
    st_subheader_with_popover(
        f"Closed Tickets without Resolution Date: {len(closed_no_resolution)} ({len(closed_no_resolution)/len(df)*100:.1f}%)",
        "**Purpose**: Identify closed tickets missing resolution timestamps, which prevents accurate SLA calculation and affects performance metrics."
    )
    if len(closed_no_resolution) > 0:
        st.warning(f"⚠️ Found {len(closed_no_resolution)} closed tickets without resolution date")
        st.dataframe(closed_no_resolution[[COL_NUMBER, COL_OPENED, COL_STATE, COL_ASSIGNMENT_GROUP, COL_SHORT_DESC]].head(10))
    else:
        st.success("✅ All closed tickets have resolution dates")
    return len(closed_no_resolution)

def _check_open_with_resolution(df):
    """Checks for open tickets that incorrectly have a resolution date."""
    open_but_resolved = df[(df[COL_STATE].isin(OPEN_STATES)) & (df[COL_RESOLVED].notna())]
    st_subheader_with_popover(
        f"Open Tickets with a Resolution Date: {len(open_but_resolved)}",
        "**Purpose**: Detect tickets that have a resolution date but are still in an open state, possibly due to workflow or data sync issues."
    )
    if len(open_but_resolved) > 0:
        st.warning(f"⚠️ Found {len(open_but_resolved)} open tickets with resolution date")
        st.dataframe(open_but_resolved[[COL_NUMBER, COL_OPENED, COL_RESOLVED, COL_STATE, COL_ASSIGNMENT_GROUP]].head(10))
    else:
        st.success("✅ No open tickets have premature resolution dates")
    return len(open_but_resolved)

def _check_missing_critical_fields(df):
    """Checks for missing data in critical ticket fields."""
    critical_fields = {
        "Priority": COL_PRIORITY, "Assignment Group": COL_ASSIGNMENT_GROUP, "Assigned To": COL_ASSIGNED_TO,
        "Short Description": COL_SHORT_DESC, "State": COL_STATE
    }
    missing_fields_summary = []
    total_missing = 0
    for name, col in critical_fields.items():
        missing_count = df[df[col].isna() | (df[col] == "")].shape[0]
        total_missing += missing_count
        missing_fields_summary.append([name, missing_count, f"{missing_count/len(df)*100:.1f}%"])
    
    missing_fields_df = pd.DataFrame(missing_fields_summary, columns=["Field", "Missing Count", "Percentage"])
    st_subheader_with_popover(
        "Missing Critical Fields Summary",
        "**Purpose**: Track completeness of essential ticket fields. Missing data impacts routing, workload tracking, and reporting."
    )
    st.dataframe(missing_fields_df, use_container_width=True)
    return total_missing

def _check_duplicate_tickets(df):
    """Checks for duplicate ticket numbers in the dataset."""
    duplicate_tickets = df[df.duplicated(subset=[COL_NUMBER], keep=False)]
    st_subheader_with_popover(
        f"Duplicate Ticket Numbers: {len(duplicate_tickets)}",
        "**Purpose**: Detect duplicate ticket records in the dataset, which can skew volume and performance metrics."
    )
    if len(duplicate_tickets) > 0:
        st.error(f"🚨 Found {len(duplicate_tickets)} records with duplicate ticket numbers")
        st.dataframe(duplicate_tickets[[COL_NUMBER, COL_OPENED, COL_STATE, COL_ASSIGNMENT_GROUP]].head(10))
    else:
        st.success("✅ No duplicate ticket numbers found")
    return len(duplicate_tickets)

def _check_future_dates(df):
    """Checks for tickets with future opened or resolved dates."""
    future_opened = df[df[COL_OPENED] > datetime.now()]
    future_resolved = df[df[COL_RESOLVED] > datetime.now()]
    total_future = len(future_opened) + len(future_resolved)
    st_subheader_with_popover(
        f"Tickets with Future Dates: {total_future}",
        "**Purpose**: Detect tickets with impossible future timestamps, which could be caused by timezone or data entry errors."
    )
    if total_future > 0:
        st.warning(f"⚠️ Found {len(future_opened)} tickets opened in future, {len(future_resolved)} resolved in future")
    else:
        st.success("✅ No tickets with future dates found")
    return total_future

def _check_orphaned_tickets(df):
    """Checks for active tickets that are not assigned to any group or person."""
    orphaned_tickets = df[
        (df[COL_ASSIGNMENT_GROUP].isna() | (df[COL_ASSIGNMENT_GROUP] == "")) &
        (df[COL_ASSIGNED_TO].isna() | (df[COL_ASSIGNED_TO] == "")) &
        (df[COL_STATE].isin(OPEN_STATES))
    ]
    st_subheader_with_popover(
        f"Orphaned Active Tickets: {len(orphaned_tickets)}",
        "**Purpose**: Identify active tickets that are not assigned to any group or person. These tickets are at risk of not being actioned."
    )
    if len(orphaned_tickets) > 0:
        st.warning(f"⚠️ Found {len(orphaned_tickets)} active tickets with no assignment group or assignee")
        st.dataframe(orphaned_tickets[[COL_NUMBER, COL_OPENED, COL_PRIORITY, COL_STATE, COL_SHORT_DESC]].head(10))
    else:
        st.success("✅ All active tickets are properly assigned")
    return len(orphaned_tickets)

def _display_quality_score(issue_count, total_tickets):
    """Calculates and displays the overall data quality score."""
    quality_score = max(0, 100 - (issue_count / total_tickets * 100))
    st_subheader_with_popover(
        "Overall Data Quality Score",
        """
        **Purpose**: Overall data quality assessment based on detected issues.
        **Calculation**: 100% - (Total Issues / Total Tickets × 100)
        **Score Guide**: 95-100% (Excellent), 85-94% (Good), 70-84% (Fair), <70% (Poor)
        """
    )
    if quality_score >= 95:
        st.success(f"🌟 Excellent: {quality_score:.1f}%")
    elif quality_score >= 85:
        st.info(f"✅ Good: {quality_score:.1f}%")
    elif quality_score >= 70:
        st.warning(f"⚠️ Fair: {quality_score:.1f}%")
    else:
        st.error(f"🚨 Poor: {quality_score:.1f}%")
    st.write(f"**Summary**: {issue_count:,} data quality issues found in {total_tickets:,} tickets (Note: some checks overlap).")


def render_quality_tab(filtered_df):
    """Renders the content for the Data Quality tab."""
    st_header_with_popover(
        "Data Quality Checks",
        """
        **Purpose**: Ensure data integrity and identify process compliance issues that could affect reporting accuracy.
        
        **Key Insights**:
        - Missing or invalid data detection
        - Process compliance monitoring
        - Data completeness assessment
        """
    )
            
    if len(filtered_df) == 0:
        st.info("No data to check for quality.")
        return

    total_tickets_dq = len(filtered_df)
    quality_issues_count = 0

    # Run all data quality checks and aggregate issue counts
    _check_unresolved_active(filtered_df)
    _check_missing_ci(filtered_df)
    quality_issues_count += _check_unusual_resolution(filtered_df)
    quality_issues_count += _check_resolved_without_opened(filtered_df)
    quality_issues_count += _check_closed_without_resolution(filtered_df)
    quality_issues_count += _check_open_with_resolution(filtered_df)
    quality_issues_count += _check_missing_critical_fields(filtered_df)
    quality_issues_count += _check_duplicate_tickets(filtered_df)
    quality_issues_count += _check_future_dates(filtered_df)
    quality_issues_count += _check_orphaned_tickets(filtered_df)
    
    # Display the final quality score
    _display_quality_score(quality_issues_count, total_tickets_dq)
    
    # Overall data quality recommendations
    if quality_issues_count > 0:
        st.write("#### Data Quality Improvement Recommendations")
        
        if quality_issues_count / total_tickets_dq > 0.1:
            st.error("🚨 **High Priority**: >10% of tickets have data quality issues - implement data governance processes")
        elif quality_issues_count / total_tickets_dq > 0.05:
            st.warning("⚠️ **Moderate Priority**: 5-10% of tickets have issues - focus on critical field validation")
        else:
            st.info("📊 **Low Priority**: <5% of tickets affected - maintain current data quality processes")
        
        st.info("💡 **Recommendations**: Focus on missing critical fields, resolve workflow state inconsistencies, and implement automated data validation rules.")


def render_data_tab(filtered_df):
    """Renders the content for the Raw Data tab."""
    st_header_with_popover(
        "Raw Data Explorer",
        """
        **Purpose**: Provide direct access to underlying ticket data for detailed investigation and custom analysis.
        
        **Key Insights**:
        - Detailed ticket examination
        - Custom filtering and sorting
        - Export capabilities for further analysis
        """
    )

    st_subheader_with_popover(
        "Data Table (showing filtered results from global filters above)",
        """
        **Purpose**: Direct access to underlying ticket data for detailed investigation.
        **Note**: Shows first 100 records of filtered dataset. Use global filters above to narrow down results.
        """
    )
    display_cols = [COL_NUMBER, COL_OPENED, COL_PRIORITY, COL_STATE, COL_ASSIGNMENT_GROUP, 
                    COL_SHORT_DESC, COL_RESOLUTION_DAYS]
    st.dataframe(filtered_df[display_cols].head(100))
    
    # Data export insights
    if len(filtered_df) > 100:
        st.info(f"📄 **Note**: Showing first 100 of {len(filtered_df):,} filtered records. Use global filters above to narrow results for detailed analysis.")
    
    # Data summary insights
    st.write("#### Dataset Summary Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_range = (filtered_df[COL_OPENED].max() - filtered_df[COL_OPENED].min()).days if len(filtered_df) > 0 else 0
        st.metric("Date Range (Days)", f"{date_range:,}")
    
    with col2:
        unique_assignees = filtered_df[COL_ASSIGNED_TO].nunique() if len(filtered_df) > 0 else 0
        st.metric("Unique Assignees", f"{unique_assignees:,}")
    
    with col3:
        unique_groups = filtered_df[COL_ASSIGNMENT_GROUP].nunique() if len(filtered_df) > 0 else 0
        st.metric("Assignment Groups", f"{unique_groups:,}")


if DEFAULT_CSV_FILE in os.listdir():
    source = DEFAULT_CSV_FILE
    st.success(f"✅ **Data Source**: Using {DEFAULT_CSV_FILE} - enhanced TCD dataset with organizational metadata")
else:
    source = st.file_uploader("Upload a ServiceNow export (CSV)", type="csv")
    if source:
        st.info("📄 **Custom Data**: Using uploaded file for analysis")

if source:
    df = load_data(source)
else:
    st.stop()

# --- Basic calcs ----------------------------------------------------
monthly_tickets = df.groupby("YearMonth").size().reset_index(name="Tickets")
monthly_tickets = monthly_tickets.sort_values("YearMonth")

# SLA compliance by priority
sla_compliance = (
    df.groupby("Priority")
    .agg(
        Total_Tickets=("Number", "count"),
        SLA_Met_Count=("SLA_Met", "sum"),
        Avg_Resolution_Hours=("Resolution_Hours", "mean")
    )
    .reset_index()
)
sla_compliance["SLA_Compliance"] = sla_compliance["SLA_Met_Count"] / sla_compliance["Total_Tickets"]

# --- UI -------------------------------------------------------------
st.title("BUMA Ticket Analysis Dashboard")
st.write("**Bukit Makmur Mandiri Utama - Comprehensive Ticket Analytics**")

# --- Global Filters at the top --------------------------------------
st.subheader("Global Filters")
col1, col2, col3 = st.columns(3)

with col1:
    # Get unique values, sort them, and handle potential NaNs
    unique_states = sorted([state for state in df["State"].unique() if pd.notna(state)])
    selected_states = st.multiselect("Filter by State", unique_states, key="global_states")

with col2:
    unique_priorities = sorted([p for p in df["Priority"].unique() if pd.notna(p)])
    selected_priorities = st.multiselect("Filter by Priority", unique_priorities, key="global_priorities")

with col3:
    unique_groups = sorted([g for g in df[COL_ASSIGNMENT_GROUP].unique() if pd.notna(g)])
    selected_groups = st.multiselect("Filter by Assignment Group", unique_groups, key="global_groups")


# Apply global filters to create filtered dataset
filtered_df = df.copy()
if selected_states:
    filtered_df = filtered_df[filtered_df["State"].isin(selected_states)]
if selected_priorities:
    filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priorities)]
if selected_groups:
    filtered_df = filtered_df[filtered_df[COL_ASSIGNMENT_GROUP].isin(selected_groups)]

st.write(f"**Showing {len(filtered_df):,} of {len(df):,} tickets**")

# --- Recalculate all metrics based on filtered data ----------------
monthly_tickets = filtered_df.groupby("YearMonth").size().reset_index(name="Tickets")
monthly_tickets = monthly_tickets.sort_values("YearMonth")

# SLA compliance by priority
sla_compliance = (
    filtered_df.groupby("Priority")
    .agg(
        Total_Tickets=("Number", "count"),
        SLA_Met_Count=("SLA_Met", "sum"),
        Avg_Resolution_Hours=("Resolution_Hours", "mean")
    )
    .reset_index()
)
if sla_compliance['Total_Tickets'].sum() > 0:
    sla_compliance["SLA_Compliance"] = sla_compliance["SLA_Met_Count"] / sla_compliance["Total_Tickets"]
else:
    sla_compliance["SLA_Compliance"] = 0.0


# Key Metrics (now based on filtered data)
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_tickets = len(filtered_df)
    st.metric("Total Tickets", f"{total_tickets:,}")

with col2:
    open_tickets = len(filtered_df[filtered_df["State"].isin(OPEN_STATES)])
    st.metric("Open Tickets", f"{open_tickets:,}")

with col3:
    avg_resolution_days = filtered_df["Resolution_Days"].mean() if len(filtered_df) > 0 else 0
    st.metric("Avg Resolution (Days)", f"{avg_resolution_days:.1f}")

with col4:
    overall_sla = filtered_df["SLA_Met"].mean() if len(filtered_df) > 0 and not filtered_df["SLA_Met"].isna().all() else 0
    st.metric("Overall SLA Compliance", f"{overall_sla:.1%}")

# Quick insights based on key metrics
if len(filtered_df) > 0:
    st.write("#### Key Performance Insights")
    col1, col2 = st.columns(2)
    
    with col1:
        # Open ticket analysis
        open_rate = (open_tickets / total_tickets * 100) if total_tickets > 0 else 0
        if open_rate > 15:
            st.warning(f"⚠️ **Open Ticket Alert**: {open_rate:.1f}% of tickets remain open - may indicate backlog issues")
        elif open_rate < 5:
            st.success(f"✅ **Excellent Closure Rate**: Only {open_rate:.1f}% tickets remain open")
        else:
            st.info(f"📊 **Normal Open Rate**: {open_rate:.1f}% of tickets are open")
    
    with col2:
        # SLA performance analysis
        if overall_sla < 0.85:
            st.error(f"🚨 **SLA Critical**: {overall_sla:.1%} compliance - immediate action required")
        elif overall_sla < 0.90:
            st.warning(f"⚠️ **SLA Warning**: {overall_sla:.1%} compliance - below BUMA minimum requirement")
        elif overall_sla < 0.95:
            st.info(f"📊 **SLA Good**: {overall_sla:.1%} compliance - above minimum, below expected target")
        else:
            st.success(f"🎆 **SLA Excellent**: {overall_sla:.1%} compliance - exceeding expected targets")


# --- Tabbed Interface for Dashboard Sections ---
tab_overview, tab_buma_sla, tab_performance, tab_categorical, tab_quality, tab_data = st.tabs([
    "📊 Overview", 
    "🎯 BUMA Contract SLA", 
    "📈 Performance Analysis", 
    "📋 Categorical Analysis", 
    "🔍 Data Quality", 
    "📁 Raw Data"
])

with tab_overview:
    render_overview_tab(filtered_df)

with tab_buma_sla:
    render_buma_sla_tab(filtered_df)

with tab_performance:
    render_performance_tab(filtered_df)

with tab_categorical:
    render_categorical_tab(filtered_df)

with tab_quality:
    render_quality_tab(filtered_df)

with tab_data:
    render_data_tab(filtered_df)