import pandas as pd
import streamlit as st
import plotly.express as px

# --- Load data ------------------------------------------------------
fact   = pd.read_csv("FactTicketsCleaned.csv", parse_dates=["OpenedDate"])
date   = pd.read_csv("DimDate.csv")
base   = pd.read_csv("BaselineVolume.csv")
sla_summary = pd.read_csv("SLAComplianceSummary.csv")

# --- Basic calcs ----------------------------------------------------
fact["YearMonth"] = fact["OpenedDate"].dt.to_period("M").astype(str)
monthly = (
    fact.groupby("YearMonth").size().reset_index(name="Tickets")
    .merge(base, how="left", on="YearMonth")
)
sla = sla_summary.rename(columns={"PriorityShort": "Priority", "SLA_Compliance": "Compliance"})

# --- UI -------------------------------------------------------------
st.title("BUMA Ticket & SLA Dashboard")

kpi = monthly.iloc[-1]
st.metric("Latest-month tickets", kpi.Tickets, 
          delta=f"{(kpi.Tickets-kpi.BaselineVolume)/kpi.BaselineVolume:.1%}")

fig1 = px.line(monthly, x="YearMonth", y=["Tickets", "BaselineVolume"],
               markers=True, labels={"value":"# Tickets", "variable":""})
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.bar(sla, x="Priority", y="Compliance",
              text=sla.Compliance.map("{:.1%}".format), labels={"Compliance":"SLA met"})
fig2.update_layout(yaxis_tickformat=".0%")
st.plotly_chart(fig2, use_container_width=True)

# The following dataframe requires a per-ticket 'SLA_Met' column which is not available
# in the provided FactTicketsCleaned.csv. It has been commented out to allow the app to run.
# st.dataframe(fact.query("SLA_Met==0")[["TicketID","Service","Priority","ResolutionMinutes"]]
#              .sort_values("ResolutionMinutes", ascending=False))

# --- Service Performance Analysis -----------------------------------
st.subheader("Service Performance")

service_perf = (
    fact.groupby("Service")
    .agg(
        Tickets=("Service", "size"),
        AvgResolutionMinutes=("ResolutionMinutes", "mean")
    )
    .reset_index()
    .sort_values("Tickets", ascending=False)
)

st.write("#### Top 10 Services by Ticket Volume")
fig3 = px.bar(service_perf.head(10), x="Service", y="Tickets",
              text_auto=True, title="Top 10 Services by Ticket Volume")
st.plotly_chart(fig3, use_container_width=True)

st.write("#### Top 10 Services by Avg. Resolution Time (minutes)")
fig4 = px.bar(service_perf.sort_values("AvgResolutionMinutes", ascending=False).head(10),
              x="Service", y="AvgResolutionMinutes", text_auto=True,
              title="Top 10 Services by Avg. Resolution Time")
st.plotly_chart(fig4, use_container_width=True)

st.write("Full Service Performance Data")
st.dataframe(service_perf)

# --- Ticket Distribution Analysis -----------------------------------
st.subheader("Ticket Distribution")

# Tickets by Channel
channel_dist = fact.groupby("Channel").size().reset_index(name="Tickets")
st.write("#### Tickets by Channel")
fig5 = px.pie(channel_dist, names="Channel", values="Tickets",
              title="Ticket Distribution by Channel")
st.plotly_chart(fig5, use_container_width=True)

# Tickets by Tower
tower_dist = fact.groupby("Tower").size().reset_index(name="Tickets")
st.write("#### Tickets by Tower")
fig6 = px.bar(tower_dist, x="Tower", y="Tickets", text_auto=True,
              title="Ticket Distribution by Tower")
st.plotly_chart(fig6, use_container_width=True)

# --- Correlation Analysis ---------------------------------------------
st.subheader("Correlation Analysis")

# Define a consistent order for priorities
priority_order = sorted(fact['PriorityShort'].unique())

st.write("#### Resolution Time Distribution by Priority")
fig7 = px.box(fact, x="PriorityShort", y="ResolutionMinutes", 
              category_orders={"PriorityShort": priority_order},
              log_y=True, title="Resolution Time Distribution by Priority (Log Scale)")
st.plotly_chart(fig7, use_container_width=True)

st.write("#### Resolution Time Distribution by Channel")
fig8 = px.box(fact, x="Channel", y="ResolutionMinutes", log_y=True,
              title="Resolution Time Distribution by Channel (Log Scale)")
st.plotly_chart(fig8, use_container_width=True)

# To keep the chart readable, let's focus on the top 10 towers by ticket volume
top_10_towers = service_perf.head(10)['Service'].tolist()
fact_top_towers = fact[fact['Tower'].isin(tower_dist.nlargest(10, 'Tickets')['Tower'])]

st.write("#### Resolution Time Distribution by Tower (Top 10)")
fig9 = px.box(fact_top_towers, x="Tower", y="ResolutionMinutes", log_y=True,
              title="Resolution Time Distribution by Tower (Top 10 by Volume, Log Scale)")
st.plotly_chart(fig9, use_container_width=True)

# --- Data Quality Checks ----------------------------------------------
st.subheader("Data Quality Checks")

# Check for tickets that are closed but not assigned to a service
unassigned_closed = fact[fact['Service'].isna() & fact['ResolvedDatetime'].notna()]
num_unassigned_closed = len(unassigned_closed)

st.write("#### Unassigned but Closed Tickets")
if num_unassigned_closed > 0:
    st.warning(f"Found {num_unassigned_closed} tickets that are closed but have no service assigned.")
    st.dataframe(unassigned_closed)
else:
    st.success("No unassigned but closed tickets were found.")