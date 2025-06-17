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

# --- Load data ------------------------------------------------------
@st.cache_data
def load_data(file):
    df = pd.read_csv(file, parse_dates=["Opened", "Resolved"], encoding="latin-1")
    
    # Clean and process data
    df["YearMonth"] = df["Opened"].dt.to_period("M").astype(str)
    df["Priority_Numeric"] = df["Priority"].str.extract(r'(\d+)').astype(int)
    df["Resolution_Days"] = (df["Resolved"] - df["Opened"]).dt.total_seconds() / (24 * 3600)
    
    # Calculate SLA metrics (assuming basic SLA targets)
    df["SLA_Target_Hours"] = df["Priority_Numeric"].map({1: 4, 2: 8, 3: 24, 4: 72})
    df["Resolution_Hours"] = df["Resolution_Days"] * 24
    df["SLA_Met"] = df["Resolution_Hours"] <= df["SLA_Target_Hours"]
    
    return df

if "Test.csv" in os.listdir():
    source = "Test.csv"
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
    unique_groups = sorted([g for g in df["Assignment group"].unique() if pd.notna(g)])
    selected_groups = st.multiselect("Filter by Assignment Group", unique_groups, key="global_groups")


# Apply global filters to create filtered dataset
filtered_df = df.copy()
if selected_states:
    filtered_df = filtered_df[filtered_df["State"].isin(selected_states)]
if selected_priorities:
    filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priorities)]
if selected_groups:
    filtered_df = filtered_df[filtered_df["Assignment group"].isin(selected_groups)]

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
    open_tickets = len(filtered_df[filtered_df["State"].isin(["Active", "Work In Progress", "Awaiting User Info"])])
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
    st.markdown("### Monthly Ticket Trends")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Track ticket volume patterns over time to identify seasonal trends, capacity planning needs, and workload fluctuations.
        
        **Key Insights**: 
        - Seasonal patterns in ticket creation
        - Growth or decline trends
        - Capacity planning indicators
        
        **Graph Explanation**: Line chart with markers showing ticket count per month. Upward trends indicate increasing workload, downward trends show improvement or seasonal effects.
        """)

    fig1 = px.line(monthly_tickets, x="YearMonth", y="Tickets",
                   markers=True, 
                   title="Monthly Ticket Volume Trend",
                   labels={"Tickets": "Number of Tickets", "YearMonth": "Month"})
    fig1.update_xaxes(tickangle=45)
    st.plotly_chart(fig1, use_container_width=True)

with tab_performance:
    st.markdown("### SLA Compliance Analysis")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Monitor service level agreement performance across different priority levels to ensure customer commitments are met.
        
        **Key Insights**:
        - P1 (4h), P2 (8h), P3 (24h), P4 (72h) targets
        - Priority-based performance gaps
        - Overall service quality metrics
        """)

    fig2 = px.bar(sla_compliance, x="Priority", y="SLA_Compliance",
                  text=sla_compliance["SLA_Compliance"].map("{:.1%}".format),
                  title="SLA Compliance by Priority Level",
                  labels={"SLA_Compliance": "SLA Compliance Rate"})
    fig2.update_layout(yaxis_tickformat=".0%")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write("#### SLA Compliance Details")
    with col2:
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Detailed breakdown of SLA performance metrics by priority level.
            
            **Columns Explained**:
            - Total_Tickets: Number of tickets for this priority
            - SLA_Met_Count: How many met their SLA target
            - Avg_Resolution_Hours: Average time to resolve
            - SLA_Compliance: Percentage meeting SLA (SLA_Met_Count/Total_Tickets)
            """)
    st.dataframe(sla_compliance.round(2))

    st.markdown("### Assignment Group Performance")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Analyze team performance, workload distribution, and identify high-performing or struggling groups.
        
        **Key Insights**:
        - Workload balance across teams
        - Team efficiency comparisons
        - Resource allocation optimization
        """)

    group_perf = (
        filtered_df.groupby("Assignment group")
        .agg(
            Tickets=("Number", "count"),
            Avg_Resolution_Hours=("Resolution_Hours", "mean"),
            SLA_Compliance=("SLA_Met", "mean")
        )
        .reset_index()
        .sort_values("Tickets", ascending=False)
    )

    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write("#### Top 15 Assignment Groups by Ticket Volume")
    with col2:
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Identify teams handling the most tickets to understand workload distribution.
            
            **Graph Explanation**: Bar chart showing ticket count per assignment group. Taller bars indicate teams with higher workloads. Text labels show exact ticket counts.
            """)
    top_groups = group_perf.head(15)
    fig3 = px.bar(top_groups, x="Assignment group", y="Tickets",
                  text_auto=True,
                  title="Top 15 Assignment Groups by Ticket Volume")
    fig3.update_xaxes(tickangle=45)
    st.plotly_chart(fig3, use_container_width=True)

    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write("#### Assignment Group SLA Performance (Top 15)")
    with col2:
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Compare team efficiency by plotting resolution time vs SLA compliance.
            
            **Graph Explanation**: Bubble scatter plot where:
            - X-axis: Average resolution time (lower is better)
            - Y-axis: SLA compliance rate (higher is better)
            - Bubble size: Total ticket volume (larger = more tickets)
            - Top-right quadrant = high performance (fast + compliant)
            """)
    fig4 = px.scatter(top_groups, x="Avg_Resolution_Hours", y="SLA_Compliance",
                      size="Tickets", hover_name="Assignment group",
                      title="Assignment Group Performance: Resolution Time vs SLA Compliance",
                      labels={"Avg_Resolution_Hours": "Average Resolution Hours", 
                             "SLA_Compliance": "SLA Compliance Rate"})
    fig4.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("### Resolution Time Analysis")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Analyze resolution efficiency across priorities and channels to identify bottlenecks and improve service delivery.
        
        **Key Insights**:
        - Priority-based resolution patterns
        - Channel efficiency comparisons
        - Performance outliers and extremes
        """)

    if len(filtered_df) > 0:
        resolution_filtered = filtered_df[filtered_df["Resolution_Hours"] <= filtered_df["Resolution_Hours"].quantile(0.95)]
    else:
        resolution_filtered = filtered_df

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Resolution Time by Priority")
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Compare resolution time distributions across priority levels.
            
            **Box Plot Elements**:
            - **Center line**: Median (50th percentile)
            - **Box edges**: Q1 (25th) and Q3 (75th percentiles)
            - **Whiskers**: Extend to 1.5×IQR from box edges
            - **Upper fence**: Q3 + 1.5×IQR (max normal value)
            - **Lower fence**: Q1 - 1.5×IQR (min normal value)
            - **Dots**: Outliers beyond fence values
            
            **Interpretation**: Smaller boxes = more consistent resolution times. P1 should have tightest distribution.
            """)
        fig7 = px.box(resolution_filtered, x="Priority", y="Resolution_Hours",
                      title="Resolution Time Distribution by Priority",
                      labels={"Resolution_Hours": "Resolution Time (Hours)"})
        st.plotly_chart(fig7, use_container_width=True)
    with col2:
        st.markdown("#### Resolution Time by Channel")
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Compare resolution efficiency across different submission channels.
            
            **Box Plot Elements**: Same as priority chart - median, quartiles, whiskers, and outliers.
            
            **Interpretation**: Channels with lower medians and smaller boxes indicate more efficient processing. Helps identify which channels may need process improvements.
            """)
        if len(filtered_df) > 0:
            top_channels = filtered_df["Channel"].value_counts().head(5).index
            channel_filtered = filtered_df[filtered_df["Channel"].isin(top_channels) & (filtered_df["Resolution_Hours"] <= filtered_df["Resolution_Hours"].quantile(0.95))]
        else:
            channel_filtered = filtered_df
        
        fig8 = px.box(channel_filtered, x="Channel", y="Resolution_Hours",
                      title="Resolution Time by Top 5 Channels",
                      labels={"Resolution_Hours": "Resolution Time (Hours)"})
        fig8.update_xaxes(tickangle=45)
        st.plotly_chart(fig8, use_container_width=True)
        
    st.markdown("### Top Assignee Performance")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Recognize high performers and identify individual workload distribution and performance patterns.
        
        **Key Insights**:
        - Individual performance metrics
        - Workload distribution fairness
        - Recognition and development opportunities
        """)
    assignee_perf = (
        filtered_df.groupby("Assigned to")
        .agg(
            Tickets=("Number", "count"),
            Avg_Resolution_Hours=("Resolution_Hours", "mean"),
            SLA_Compliance=("SLA_Met", "mean")
        )
        .reset_index()
        .sort_values("Tickets", ascending=False)
        .head(20)
    )
    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write("#### Top 20 Assignees by Ticket Volume")
    with col2:
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Individual performance analysis and workload distribution.
            
            **Metrics Explained**:
            - **Tickets**: Total assigned tickets
            - **Avg_Resolution_Hours**: Individual efficiency metric
            - **SLA_Compliance**: Personal SLA performance rate
            
            **Use Cases**: Performance reviews, workload balancing, training needs identification.
            """)
    st.dataframe(assignee_perf.round(2))

with tab_categorical:
    st.markdown("### Channel and Location Distribution")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Understand how users submit tickets and where issues originate to optimize support channels and regional resources.
        
        **Key Insights**:
        - Preferred communication channels
        - Geographic distribution of issues
        - Channel-specific resolution patterns
        """)

    col1, col2 = st.columns(2)
    with col1:
        col_inner1, col_inner2 = st.columns([0.92, 0.08])
        with col_inner1:
            st.write("#### Ticket Distribution by Channel")
        with col_inner2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Show how users prefer to submit tickets.
                
                **Graph Explanation**: Pie chart showing percentage breakdown of ticket submission channels. Larger slices indicate more popular channels.
                """)
        channel_dist = filtered_df.groupby("Channel").size().reset_index(name="Tickets")
        fig5 = px.pie(channel_dist, names="Channel", values="Tickets",
                      title="Ticket Distribution by Channel")
        st.plotly_chart(fig5, use_container_width=True)
    with col2:
        col_inner1, col_inner2 = st.columns([0.92, 0.08])
        with col_inner1:
            st.write("#### Top 10 Locations by Volume")
        with col_inner2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Identify geographic hotspots requiring more support resources.
                
                **Graph Explanation**: Bar chart of top 10 locations by ticket count. Helps identify sites needing additional IT support or infrastructure improvements.
                """)
        location_dist = filtered_df.groupby("Location").size().reset_index(name="Tickets").nlargest(10, 'Tickets')
        fig6 = px.bar(location_dist, x="Location", y="Tickets",
                      title="Top 10 Locations by Ticket Volume")
        fig6.update_xaxes(tickangle=45)
        st.plotly_chart(fig6, use_container_width=True)

    st.markdown("### Ticket State Analysis")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Monitor ticket lifecycle and identify potential process bottlenecks or workflow issues.
        
        **Key Insights**:
        - Workflow distribution analysis
        - Process bottleneck identification
        - Closure rate monitoring
        """)

    state_summary = filtered_df.groupby("State").size().reset_index(name="Count")
    if state_summary["Count"].sum() > 0:
        state_summary["Percentage"] = (state_summary["Count"] / state_summary["Count"].sum() * 100).round(1)
    else:
        state_summary["Percentage"] = 0.0
        
    col1, col2 = st.columns(2)
    with col1:
        col_inner1, col_inner2 = st.columns([0.92, 0.08])
        with col_inner1:
            st.write("#### Distribution by State")
        with col_inner2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Monitor ticket lifecycle stages and identify potential bottlenecks.
                
                **Graph Explanation**: Pie chart showing percentage of tickets in each workflow state. Large "Work In Progress" slice may indicate bottlenecks.
                """)
        fig9 = px.pie(state_summary, names="State", values="Count",
                      title="Ticket Distribution by State")
        st.plotly_chart(fig9, use_container_width=True)
    with col2:
        col_inner1, col_inner2 = st.columns([0.92, 0.08])
        with col_inner1:
            st.write("#### Ticket State Summary")
        with col_inner2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Detailed breakdown of ticket states with counts and percentages.
                
                **Table Explanation**: Shows exact numbers and percentages for each workflow state. Use to identify process bottlenecks or closure rates.
                """)
        st.dataframe(state_summary, use_container_width=True)

    st.markdown("### Categorization Analysis")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Identify the most common types of issues to focus improvement efforts and knowledge base development.
        
        **Key Insights**:
        - Common problem patterns
        - Knowledge management opportunities
        - Process improvement focus areas
        """)

    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write("#### Top 15 Categories by Volume")
    with col2:
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Identify most common issue types to focus improvement efforts.
            
            **Graph Explanation**: Bar chart of top 15 ticket categories by volume. Helps prioritize:
            - Knowledge base articles
            - Process improvements
            - Training needs
            - Self-service solutions
            """)
            
    cat_summary = filtered_df.groupby("Categorization").size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)
    fig10 = px.bar(cat_summary.head(15), x="Categorization", y="Tickets",
                   title="Top 15 Categories by Volume",
                   text_auto=True)
    fig10.update_xaxes(tickangle=45)
    st.plotly_chart(fig10, use_container_width=True)

with tab_quality:
    st.markdown("### Data Quality Checks")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Ensure data integrity and identify process compliance issues that could affect reporting accuracy.
        
        **Key Insights**:
        - Missing or invalid data detection
        - Process compliance monitoring
        - Data completeness assessment
        """)
            
    if len(filtered_df) == 0:
        st.info("No data to check for quality.")
    else:
        unresolved_active = filtered_df[filtered_df["Resolved"].isna() & filtered_df["State"].isin(["Active", "Work In Progress"])]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            st.write(f"#### Active Tickets without Resolution Date: {len(unresolved_active)}")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Identify active tickets missing resolution timestamps.
                
                **Data Quality Issue**: Active/WIP tickets should not have resolution dates, but this metric tracks if there are any anomalies in the data.
                """)

        missing_ci = filtered_df[filtered_df["Configuration item"].isna() | (filtered_df["Configuration item"] == "CI_notfound")]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            st.write(f"#### Tickets with Missing/Invalid Configuration Items: {len(missing_ci)} ({len(missing_ci)/len(filtered_df)*100:.1f}%)")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Track data completeness for configuration item field.
                
                **Impact**: Missing CIs make it harder to:
                - Identify recurring issues with specific systems
                - Plan maintenance and upgrades
                - Track asset performance
                """)

        unusual_resolution = filtered_df[(filtered_df["Resolution_Days"] < 0) | (filtered_df["Resolution_Days"] > 365)]
        if len(unusual_resolution) > 0:
            col1, col2 = st.columns([0.92, 0.08])
            with col1:
                st.warning(f"🚨 Found {len(unusual_resolution)} tickets with unusual resolution times (negative or >365 days)")
            with col2:
                with st.popover("❓"):
                    st.markdown("""
                    **Purpose**: Detect data quality issues with resolution times.
                    
                    **Issues Detected**:
                    - Negative times: Resolution before opened (data error)
                    - >365 days: Extremely long resolution (process issue)
                    """)
            st.dataframe(unusual_resolution[["Number", "Opened", "Resolved", "Resolution_Days", "State"]].head(10))

        no_open_but_resolved = filtered_df[filtered_df["Opened"].isna() & filtered_df["Resolved"].notna()]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            if len(no_open_but_resolved) > 0:
                st.error(f"🚨 Found {len(no_open_but_resolved)} tickets with resolution date but no opening date")
            else:
                st.success("✅ No tickets found with resolution date but missing opening date")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Identify tickets with impossible data - resolved without being opened.
                
                **Impact**: These records are likely data import errors and should be investigated or cleaned.
                """)
        if len(no_open_but_resolved) > 0:
            st.dataframe(no_open_but_resolved[["Number", "Opened", "Resolved", "State", "Short description"]].head(10))

        closed_no_resolution = filtered_df[
            (filtered_df["State"].isin(["Closed", "Resolved", "Cancelled"])) & 
            (filtered_df["Resolved"].isna())
        ]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            if len(closed_no_resolution) > 0:
                st.warning(f"⚠️ Found {len(closed_no_resolution)} closed tickets without resolution date ({len(closed_no_resolution)/len(filtered_df)*100:.1f}%)")
            else:
                st.success("✅ All closed tickets have resolution dates")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Identify closed tickets missing resolution timestamps.
                
                **Impact**: 
                - Prevents accurate SLA calculation
                - Affects performance metrics
                - May indicate process gaps in ticket closure
                """)
        if len(closed_no_resolution) > 0:
            st.dataframe(closed_no_resolution[["Number", "Opened", "State", "Assignment group", "Short description"]].head(10))

        open_but_resolved = filtered_df[
            (filtered_df["State"].isin(["Active", "Work In Progress", "New", "Awaiting User Info"])) & 
            (filtered_df["Resolved"].notna())
        ]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            if len(open_but_resolved) > 0:
                st.warning(f"⚠️ Found {len(open_but_resolved)} open tickets with resolution date")
            else:
                st.success("✅ No open tickets have premature resolution dates")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Detect tickets marked as resolved but still in open state.
                
                **Possible Causes**:
                - Workflow state not updated after resolution
                - Tickets reopened but resolution date not cleared
                - Data synchronization issues
                """)
        if len(open_but_resolved) > 0:
            st.dataframe(open_but_resolved[["Number", "Opened", "Resolved", "State", "Assignment group"]].head(10))

        missing_fields_summary = []
        missing_priority = filtered_df[filtered_df["Priority"].isna() | (filtered_df["Priority"] == "")]
        missing_fields_summary.append(["Priority", len(missing_priority), f"{len(missing_priority)/len(filtered_df)*100:.1f}%"])
        missing_assignment = filtered_df[filtered_df["Assignment group"].isna() | (filtered_df["Assignment group"] == "")]
        missing_fields_summary.append(["Assignment Group", len(missing_assignment), f"{len(missing_assignment)/len(filtered_df)*100:.1f}%"])
        missing_assignee = filtered_df[filtered_df["Assigned to"].isna() | (filtered_df["Assigned to"] == "")]
        missing_fields_summary.append(["Assigned To", len(missing_assignee), f"{len(missing_assignee)/len(filtered_df)*100:.1f}%"])
        missing_description = filtered_df[filtered_df["Short description"].isna() | (filtered_df["Short description"] == "")]
        missing_fields_summary.append(["Short Description", len(missing_description), f"{len(missing_description)/len(filtered_df)*100:.1f}%"])
        missing_state = filtered_df[filtered_df["State"].isna() | (filtered_df["State"] == "")]
        missing_fields_summary.append(["State", len(missing_state), f"{len(missing_state)/len(filtered_df)*100:.1f}%"])
        missing_fields_df = pd.DataFrame(missing_fields_summary, columns=["Field", "Missing Count", "Percentage"])
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            st.write("#### Missing Critical Fields Summary")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Track completeness of essential ticket fields.
                
                **Impact of Missing Fields**:
                - **Priority**: Affects SLA calculation and routing
                - **Assignment Group**: Prevents proper workload tracking
                - **Assigned To**: Individual accountability issues
                - **Short Description**: Impacts searchability and reporting
                - **State**: Workflow tracking problems
                """)
        st.dataframe(missing_fields_df, use_container_width=True)

        duplicate_tickets = filtered_df[filtered_df.duplicated(subset=["Number"], keep=False)]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            if len(duplicate_tickets) > 0:
                st.error(f"🚨 Found {len(duplicate_tickets)} records with duplicate ticket numbers")
            else:
                st.success("✅ No duplicate ticket numbers found")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Detect duplicate ticket records in the dataset.
                
                **Impact**: 
                - Skews volume metrics
                - Double-counts performance metrics
                - May indicate data import issues
                """)
        if len(duplicate_tickets) > 0:
            st.dataframe(duplicate_tickets[["Number", "Opened", "State", "Assignment group"]].head(10))

        future_opened = filtered_df[filtered_df["Opened"] > datetime.now()]
        future_resolved = filtered_df[filtered_df["Resolved"] > datetime.now()]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            if len(future_opened) > 0 or len(future_resolved) > 0:
                st.warning(f"⚠️ Found {len(future_opened)} tickets opened in future, {len(future_resolved)} resolved in future")
            else:
                st.success("✅ No tickets with future dates found")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Detect tickets with impossible future timestamps.
                
                **Possible Causes**:
                - Timezone conversion errors
                - Data entry mistakes
                - System clock issues during import
                """)

        orphaned_tickets = filtered_df[
            (filtered_df["Assignment group"].isna() | (filtered_df["Assignment group"] == "")) &
            (filtered_df["Assigned to"].isna() | (filtered_df["Assigned to"] == "")) &
            (filtered_df["State"].isin(["Active", "Work In Progress", "New"]))
        ]
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            if len(orphaned_tickets) > 0:
                st.warning(f"⚠️ Found {len(orphaned_tickets)} active tickets with no assignment group or assignee")
            else:
                st.success("✅ All active tickets are properly assigned")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Identify active tickets that may be lost in the system.
                
                **Risk**: These tickets might not be worked on and could breach SLA.
                **Action**: Review and assign to appropriate teams.
                """)
        if len(orphaned_tickets) > 0:
            st.dataframe(orphaned_tickets[["Number", "Opened", "Priority", "State", "Short description"]].head(10))

        total_tickets_dq = len(filtered_df)
        quality_issues = (
            len(unusual_resolution) +
            len(no_open_but_resolved) +
            len(closed_no_resolution) +
            len(open_but_resolved) +
            len(missing_priority) +
            len(missing_assignment) +
            len(missing_assignee) +
            len(missing_description) +
            len(missing_state) +
            len(duplicate_tickets) +
            len(future_opened) +
            len(future_resolved) +
            len(orphaned_tickets)
        )
        quality_score = max(0, 100 - (quality_issues / total_tickets_dq * 100))
        
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            st.write("#### Overall Data Quality Score")
            if quality_score >= 95:
                st.success(f"🌟 Excellent: {quality_score:.1f}%")
            elif quality_score >= 85:
                st.info(f"✅ Good: {quality_score:.1f}%")
            elif quality_score >= 70:
                st.warning(f"⚠️ Fair: {quality_score:.1f}%")
            else:
                st.error(f"🚨 Poor: {quality_score:.1f}%")
        with col2:
            with st.popover("❓"):
                st.markdown("""
                **Purpose**: Overall data quality assessment based on detected issues.
                
                **Calculation**: 100% - (Total Issues / Total Tickets × 100)
                
                **Score Guide**:
                - 95-100%: Excellent data quality
                - 85-94%: Good data quality
                - 70-84%: Fair data quality (needs attention)
                - <70%: Poor data quality (requires immediate action)
                """)
        st.write(f"**Summary**: {quality_issues:,} quality issues found in {total_tickets_dq:,} tickets")

with tab_data:
    st.markdown("### Raw Data Explorer")
    with st.popover("❓"):
        st.markdown("""
        **Purpose**: Provide direct access to underlying ticket data for detailed investigation and custom analysis.
        
        **Key Insights**:
        - Detailed ticket examination
        - Custom filtering and sorting
        - Export capabilities for further analysis
        """)

    col1, col2 = st.columns([0.92, 0.08])
    with col1:
        st.write("**Data Table (showing filtered results from global filters above)**")
    with col2:
        with st.popover("❓"):
            st.markdown("""
            **Purpose**: Direct access to underlying ticket data for detailed investigation.
            
            **Columns Shown**:
            - **Number**: Unique ticket ID
            - **Opened**: Creation timestamp
            - **Priority**: Business priority level
            - **State**: Current workflow status
            - **Assignment group**: Responsible team
            - **Short description**: Issue summary
            - **Resolution_Days**: Time to resolve
            
            **Note**: Shows first 100 records of filtered dataset. Use global filters above to narrow down results.
            """)
    st.dataframe(filtered_df[["Number", "Opened", "Priority", "State", "Assignment group", 
                             "Short description", "Resolution_Days"]].head(100))