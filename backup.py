import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- Custom CSS to make the app wider ---------------------------------
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
</style>
""", unsafe_allow_html=True)

# --- Load data ------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("Test.csv", parse_dates=["Opened", "Resolved"], encoding='latin-1')
    
    # Clean and process data
    df["YearMonth"] = df["Opened"].dt.to_period("M").astype(str)
    df["Priority_Numeric"] = df["Priority"].str.extract(r'(\d+)').astype(int)
    df["Resolution_Days"] = (df["Resolved"] - df["Opened"]).dt.total_seconds() / (24 * 3600)
    
    # Calculate SLA metrics (assuming basic SLA targets)
    df["SLA_Target_Hours"] = df["Priority_Numeric"].map({1: 4, 2: 8, 3: 24, 4: 72})
    df["Resolution_Hours"] = df["Resolution_Days"] * 24
    df["SLA_Met"] = df["Resolution_Hours"] <= df["SLA_Target_Hours"]
    
    return df

df = load_data()

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
st.title("BUMA Test.csv Ticket Analysis Dashboard")
st.write("**Bukit Makmur Mandiri Utama - Comprehensive Ticket Analytics**")

# --- Global Filters at the top --------------------------------------
st.subheader("Global Filters")
col1, col2, col3 = st.columns(3)

with col1:
    selected_states = st.multiselect("Filter by State", df["State"].unique(), key="global_states")

with col2:
    selected_priorities = st.multiselect("Filter by Priority", df["Priority"].unique(), key="global_priorities")

with col3:
    selected_groups = st.multiselect("Filter by Assignment Group", df["Assignment group"].unique(), key="global_groups")

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
sla_compliance["SLA_Compliance"] = sla_compliance["SLA_Met_Count"] / sla_compliance["Total_Tickets"]

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

# --- Monthly Ticket Trends ------------------------------------------
st.subheader("Monthly Ticket Trends")

fig1 = px.line(monthly_tickets, x="YearMonth", y="Tickets",
               markers=True, 
               title="Monthly Ticket Volume Trend",
               labels={"Tickets": "Number of Tickets", "YearMonth": "Month"})
fig1.update_xaxes(tickangle=45)
st.plotly_chart(fig1, use_container_width=True)

# --- SLA Compliance Analysis ----------------------------------------
st.subheader("SLA Compliance Analysis")

fig2 = px.bar(sla_compliance, x="Priority", y="SLA_Compliance",
              text=sla_compliance["SLA_Compliance"].map("{:.1%}".format),
              title="SLA Compliance by Priority Level",
              labels={"SLA_Compliance": "SLA Compliance Rate"})
fig2.update_layout(yaxis_tickformat=".0%")
fig2.update_traces(textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

# SLA Details Table
st.write("#### SLA Compliance Details")
st.dataframe(sla_compliance.round(2))

# --- Assignment Group Performance -----------------------------------
st.subheader("Assignment Group Performance")

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

st.write("#### Top 15 Assignment Groups by Ticket Volume")
top_groups = group_perf.head(15)
fig3 = px.bar(top_groups, x="Assignment group", y="Tickets",
              text_auto=True,
              title="Top 15 Assignment Groups by Ticket Volume")
fig3.update_xaxes(tickangle=45)
st.plotly_chart(fig3, use_container_width=True)

st.write("#### Assignment Group SLA Performance (Top 15)")
fig4 = px.scatter(top_groups, x="Avg_Resolution_Hours", y="SLA_Compliance",
                  size="Tickets", hover_name="Assignment group",
                  title="Assignment Group Performance: Resolution Time vs SLA Compliance",
                  labels={"Avg_Resolution_Hours": "Average Resolution Hours", 
                         "SLA_Compliance": "SLA Compliance Rate"})
fig4.update_layout(yaxis_tickformat=".0%")
st.plotly_chart(fig4, use_container_width=True)

# --- Channel and Location Analysis ----------------------------------
st.subheader("Channel and Location Distribution")

col1, col2 = st.columns(2)

with col1:
    channel_dist = filtered_df.groupby("Channel").size().reset_index(name="Tickets")
    fig5 = px.pie(channel_dist, names="Channel", values="Tickets",
                  title="Ticket Distribution by Channel")
    st.plotly_chart(fig5, use_container_width=True)

with col2:
    location_dist = filtered_df.groupby("Location").size().reset_index(name="Tickets").head(10)
    fig6 = px.bar(location_dist, x="Location", y="Tickets",
                  title="Top 10 Locations by Ticket Volume")
    fig6.update_xaxes(tickangle=45)
    st.plotly_chart(fig6, use_container_width=True)

# --- Resolution Time Analysis ---------------------------------------
st.subheader("Resolution Time Analysis")

# Filter out extreme outliers for better visualization
resolution_filtered = filtered_df[filtered_df["Resolution_Hours"] <= filtered_df["Resolution_Hours"].quantile(0.95)]

col1, col2 = st.columns(2)

with col1:
    fig7 = px.box(resolution_filtered, x="Priority", y="Resolution_Hours",
                  title="Resolution Time Distribution by Priority",
                  labels={"Resolution_Hours": "Resolution Time (Hours)"})
    st.plotly_chart(fig7, use_container_width=True)

with col2:
    # Top channels by volume for readability
    top_channels = filtered_df["Channel"].value_counts().head(5).index
    channel_filtered = filtered_df[filtered_df["Channel"].isin(top_channels) & (filtered_df["Resolution_Hours"] <= filtered_df["Resolution_Hours"].quantile(0.95))]
    
    fig8 = px.box(channel_filtered, x="Channel", y="Resolution_Hours",
                  title="Resolution Time by Top 5 Channels",
                  labels={"Resolution_Hours": "Resolution Time (Hours)"})
    fig8.update_xaxes(tickangle=45)
    st.plotly_chart(fig8, use_container_width=True)

# --- State Analysis -------------------------------------------------
st.subheader("Ticket State Analysis")

state_summary = filtered_df.groupby("State").size().reset_index(name="Count")
state_summary["Percentage"] = (state_summary["Count"] / state_summary["Count"].sum() * 100).round(1)

col1, col2 = st.columns(2)

with col1:
    fig9 = px.pie(state_summary, names="State", values="Count",
                  title="Ticket Distribution by State")
    st.plotly_chart(fig9, use_container_width=True)

with col2:
    st.write("#### Ticket State Summary")
    st.dataframe(state_summary, use_container_width=True)

# --- Categorization Analysis ----------------------------------------
st.subheader("Categorization Analysis")

cat_summary = filtered_df.groupby("Categorization").size().reset_index(name="Tickets").sort_values("Tickets", ascending=False)

fig10 = px.bar(cat_summary.head(15), x="Categorization", y="Tickets",
               title="Top 15 Categories by Volume",
               text_auto=True)
fig10.update_xaxes(tickangle=45)
st.plotly_chart(fig10, use_container_width=True)

# --- Data Quality Checks --------------------------------------------
st.subheader("Data Quality Checks")

# Missing resolved dates
unresolved_active = filtered_df[filtered_df["Resolved"].isna() & filtered_df["State"].isin(["Active", "Work In Progress"])]
st.write(f"#### Active Tickets without Resolution Date: {len(unresolved_active)}")

# Tickets with missing configuration items
missing_ci = filtered_df[filtered_df["Configuration item"].isna() | (filtered_df["Configuration item"] == "CI_notfound")]
st.write(f"#### Tickets with Missing/Invalid Configuration Items: {len(missing_ci)} ({len(missing_ci)/len(filtered_df)*100:.1f}%)")

# Unusual resolution times (negative or extremely long)
unusual_resolution = filtered_df[(filtered_df["Resolution_Days"] < 0) | (filtered_df["Resolution_Days"] > 365)]
if len(unusual_resolution) > 0:
    st.warning(f"Found {len(unusual_resolution)} tickets with unusual resolution times (negative or >365 days)")
    st.dataframe(unusual_resolution[["Number", "Opened", "Resolved", "Resolution_Days", "State"]].head(10))

# --- Assignee Performance -------------------------------------------
st.subheader("Top Assignee Performance")

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

st.write("#### Top 20 Assignees by Ticket Volume")
st.dataframe(assignee_perf.round(2))

# --- Raw Data Explorer ----------------------------------------------
st.subheader("Raw Data Explorer")

st.write("**Data Table (showing filtered results from global filters above)**")
st.dataframe(filtered_df[["Number", "Opened", "Priority", "State", "Assignment group", 
                         "Short description", "Resolution_Days"]].head(100))