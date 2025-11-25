# streamlit_app.py
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import os

st.set_page_config(page_title="Energy Dashboard", page_icon="🌍", layout="wide")

st.markdown("## 🌍 Energy & Carbon Emission Dashboard")


DATA_PATH = "global_energy_consumption.csv"  # ganti path jika perlu

@st.cache_data
def load_data(path=DATA_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_csv(path)
    # bersihkan header whitespace
    df.columns = [c.strip() for c in df.columns]

    # pastikan kolom yang kita butuhkan ada
    required = ['Country','Year','Total Energy Consumption (TWh)',
                'Renewable Energy Share (%)','Fossil Fuel Dependency (%)']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    # normalisasi tipe
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
    df['Total Energy Consumption (TWh)'] = pd.to_numeric(df['Total Energy Consumption (TWh)'], errors='coerce').fillna(0)
    df['Renewable Energy Share (%)'] = pd.to_numeric(df['Renewable Energy Share (%)'], errors='coerce').fillna(0)
    df['Fossil Fuel Dependency (%)'] = pd.to_numeric(df['Fossil Fuel Dependency (%)'], errors='coerce').fillna(0)

    return df

# ---------- load ----------
try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
countries = ["All"] + sorted(df['Country'].dropna().unique().tolist())
country = st.sidebar.selectbox("Country", countries, index=0)

years = sorted(df['Year'].dropna().astype(int).unique().tolist())
ymin, ymax = int(min(years)), int(max(years))
year_range = st.sidebar.slider("Year range", ymin, ymax, (ymin, ymax), step=1)

# apply filters
df_f = df[(df['Year'] >= year_range[0]) & (df['Year'] <= year_range[1])]
if country != "All":
    df_f = df_f[df_f['Country'] == country]

# ---------- KPI ----------
total_energy = df_f['Total Energy Consumption (TWh)'].sum()
avg_renew = df_f['Renewable Energy Share (%)'].mean()
avg_foss = df_f['Fossil Fuel Dependency (%)'].mean()
avg_percap = df_f['Per Capita Energy Use (kWh)'].mean() if 'Per Capita Energy Use (kWh)' in df_f.columns else np.nan
carbon = df_f['Carbon Emissions (Million Tons)'].sum() if 'Carbon Emissions (Million Tons)' in df_f.columns else np.nan

c1,c2,c3,c4,c5 = st.columns([1.4,1,1,1,1])
c1.metric("Total Energy (TWh)", f"{total_energy:,.0f}")
c2.metric("Avg Renewable Share (%)", f"{avg_renew:.2f}%")
c3.metric("Avg Fossil Dependency (%)", f"{avg_foss:.2f}%")
c4.metric("Per Capita (kWh)", f"{avg_percap:.0f}" if not np.isnan(avg_percap) else "N/A")
c5.metric("Carbon Emissions (Mt)", f"{carbon:,.1f}" if not np.isnan(carbon) else "N/A")

st.markdown("---")

# ---------- Chart A: Fossil vs Renewable (2 lines) ----------
st.markdown("### Fossil vs Renewable — Trend")

# Aggregate per year (mean of percentages is appropriate)
agg_pct = df_f.groupby('Year').agg({
    'Renewable Energy Share (%)':'mean',
    'Fossil Fuel Dependency (%)':'mean'
}).reset_index().rename(columns={
    'Renewable Energy Share (%)':'Renewable',
    'Fossil Fuel Dependency (%)':'Fossil'
})

# prepare for altair fold
chartA = alt.Chart(agg_pct).transform_fold(
    fold=['Fossil','Renewable'],
    as_=['Source','Value']
).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Year'),
    y=alt.Y('Value:Q', title='Share (%)'),
    color=alt.Color('Source:N', legend=alt.Legend(title='Source')),
    tooltip=[alt.Tooltip('Year:O'), alt.Tooltip('Source:N'), alt.Tooltip('Value:Q', format='.2f')]
).properties(height=340).interactive()

st.altair_chart(chartA, use_container_width=True)

st.markdown("---")

# ---------- Chart B: Share (%) stacked area & Total Consumption line ----------
st.markdown("### Bauran Energi (Share %) & Total Konsumsi (TWh)")

# gunakan Renewable dan Fossil sebagai dua kelas; jika ada selisih (Other) biarkan
mix = agg_pct.copy()
# convert percentages to fraction for area stacking
mix_long = mix.melt(id_vars='Year', value_vars=['Fossil','Renewable'], var_name='EnergyType', value_name='Pct')
mix_long['Frac'] = mix_long['Pct'] / 100.0

area = alt.Chart(mix_long).mark_area().encode(
    x=alt.X('Year:O', title='Year'),
    y=alt.Y('Frac:Q', title='Share (fraction)', axis=alt.Axis(format='%')),
    color=alt.Color('EnergyType:N', title='Energy Type'),
    tooltip=[alt.Tooltip('Year:O'), alt.Tooltip('EnergyType:N'), alt.Tooltip('Pct:Q', format='.2f', title='Share (%)')]
).properties(height=340).interactive()

# total consumption line
cons = df_f.groupby('Year')['Total Energy Consumption (TWh)'].sum().reset_index()
line_total = alt.Chart(cons).mark_line(point=True).encode(
    x=alt.X('Year:O'),
    y=alt.Y('Total Energy Consumption (TWh):Q', title='Total Energy (TWh)'),
    tooltip=[alt.Tooltip('Year:O'), alt.Tooltip('Total Energy Consumption (TWh):Q', format=',.0f')]
).properties(height=340).interactive()

# tampilkan side-by-side
left, right = st.columns(2)
with left:
    st.altair_chart(area, use_container_width=True)
with right:
    st.altair_chart(line_total, use_container_width=True)

st.markdown("---")
