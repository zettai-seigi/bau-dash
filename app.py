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

# --- Filename Constant -------------------------------------------------
DEFAULT_CSV_FILE = "Test.csv"

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
    df = pd.read_csv(file, parse_dates=[COL_OPENED, COL_RESOLVED], encoding="latin-1")
    
    # Clean and process data
    df[COL_YEAR_MONTH] = df[COL_OPENED].dt.to_period("M").astype(str)
    df[COL_PRIORITY_NUMERIC] = df[COL_PRIORITY].str.extract(r'(\d+)').astype(int)
    df[COL_RESOLUTION_DAYS] = (df[COL_RESOLVED] - df[COL_OPENED]).dt.total_seconds() / (24 * 3600)
    
    # Calculate SLA metrics (assuming basic SLA targets)
    df[COL_SLA_TARGET_HOURS] = df[COL_PRIORITY_NUMERIC].map({1: 4, 2: 8, 3: 24, 4: 72})
    df[COL_RESOLUTION_HOURS] = df[COL_RESOLUTION_DAYS] * 24
    df[COL_SLA_MET] = df[COL_RESOLUTION_HOURS] <= df[COL_SLA_TARGET_HOURS]
    
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

def render_performance_tab(filtered_df):
    """Renders the content for the Performance Analysis tab."""
    st_header_with_popover(
        "SLA Compliance Analysis",
        """
        **Purpose**: Monitor service level agreement performance across different priority levels to ensure customer commitments are met.
        
        **Key Insights**:
        - P1 (4h), P2 (8h), P3 (24h), P4 (72h) targets
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
    st.dataframe(sla_compliance.round(2))

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
        fig7 = px.box(resolution_filtered, x=COL_PRIORITY, y=COL_RESOLUTION_HOURS,
                      title="Resolution Time Distribution by Priority",
                      labels={COL_RESOLUTION_HOURS: "Resolution Time (Hours)"})
        st.plotly_chart(fig7, use_container_width=True)
    with col2:
        st.markdown("#### Resolution Time by Channel")
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Compare resolution efficiency across different submission channels.
            **Interpretation**: Channels with lower medians and smaller boxes indicate more efficient processing.
            """)
        if len(filtered_df) > 0:
            top_channels = filtered_df[COL_CHANNEL].value_counts().head(5).index
            channel_filtered = resolution_filtered[resolution_filtered[COL_CHANNEL].isin(top_channels)]
        else:
            channel_filtered = filtered_df
        
        fig8 = px.box(channel_filtered, x=COL_CHANNEL, y=COL_RESOLUTION_HOURS,
                      title="Resolution Time by Top 5 Channels",
                      labels={COL_RESOLUTION_HOURS: "Resolution Time (Hours)"})
        fig8.update_xaxes(tickangle=45)
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
    st.dataframe(assignee_perf.round(2))

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
        channel_monthly = filtered_df.dropna(subset=[COL_CHANNEL]).groupby([COL_YEAR_MONTH, COL_CHANNEL]).size().reset_index(name='Tickets')

        if not channel_monthly.empty:
            channel_pivot = channel_monthly.pivot_table(index=COL_CHANNEL, columns=COL_YEAR_MONTH, values='Tickets', fill_value=0)
            channel_pivot = channel_pivot.reindex(sorted(channel_pivot.columns), axis=1)

            if not channel_pivot.empty:
                grand_total_row = channel_pivot.sum().rename('Grand Total')
                channel_pivot_with_total = pd.concat([channel_pivot, pd.DataFrame(grand_total_row).T])
            else:
                channel_pivot_with_total = channel_pivot

            st.write("#### Ticket Channel Breakdown by Month")
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
            "Ticket Distribution by Channel",
            """
            **Purpose**: Show how users prefer to submit tickets.
            **Graph Explanation**: Pie chart showing percentage breakdown of ticket submission channels. Larger slices indicate more popular channels.
            """
        )
        channel_dist = filtered_df.groupby(COL_CHANNEL).size().reset_index(name="Tickets")
        fig5 = px.pie(channel_dist, names=COL_CHANNEL, values="Tickets",
                      title="Ticket Distribution by Channel")
        st.plotly_chart(fig5, use_container_width=True)
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


if DEFAULT_CSV_FILE in os.listdir():
    source = DEFAULT_CSV_FILE
else:
    source = st.file_uploader("Upload a ServiceNow export (CSV)", type="csv")

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


# --- Tabbed Interface for Dashboard Sections ---
tab_overview, tab_performance, tab_categorical, tab_quality, tab_data = st.tabs([
    "📊 Overview", 
    "🎯 Performance Analysis", 
    "📈 Categorical Analysis", 
    "🔍 Data Quality", 
    "📋 Raw Data"
])

with tab_overview:
    render_overview_tab(filtered_df)

with tab_performance:
    render_performance_tab(filtered_df)

with tab_categorical:
    render_categorical_tab(filtered_df)

with tab_quality:
    render_quality_tab(filtered_df)

with tab_data:
    render_data_tab(filtered_df)