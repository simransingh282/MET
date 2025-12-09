import streamlit as st
import pandas as pd
from metpy.units import units
from metpy.calc import k_index, lifted_index, showalter_index
import altair as alt

# ------------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="Thunderstorm Estimator",
    layout="wide",
    page_icon="🌩️"
)

# ------------------- SMALL CSS TWEAKS -------------------
st.markdown("""
    <style>
        .big-title {
            font-size: 32px !important;
            font-weight: 700 !important;
        }
        .sub {
            font-size: 16px !important;
            color: #555;
        }
        .card {
            padding: 1rem;
            border-radius: 0.8rem;
            border: 1px solid #e0e0e0;
            background-color: #f9fafb;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown('<p class="big-title">🌩️ Thunderstorm Chance from Sounding File</p>', unsafe_allow_html=True)
st.markdown('<p class="sub">Upload your STA / sounding file and get K-Index, Lifted Index, Showalter Index and a final thunderstorm assessment with visualizations.</p>', unsafe_allow_html=True)

st.write("")

# ------------------- LAYOUT: SIDEBAR FOR UPLOAD -------------------
with st.sidebar:
    st.header("📂 Upload Data")
    uploaded_file = st.file_uploader(
        "Upload your STA file (.xls/.xlsx/.csv)",
        type=["xls", "xlsx", "csv"]
    )
    st.markdown("---")
    st.markdown("**Tip:** For your file, it will usually detect:")
    st.markdown("- Temperature → `Temperature`")
    st.markdown("- Dew Point → `Dew Point`")
    st.markdown("- Pressure → `Derived Pressure`")

# ------------------- MAIN LOGIC -------------------
if uploaded_file is not None:
    # Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("✅ File uploaded successfully!")

    with st.expander("📄 Preview data (top 10 rows)", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    # Auto-detect columns
    temp_col = None
    dew_col = None
    press_col = None
    alt_col = None

    for col in df.columns:
        name = col.lower()
        if "temp" in name and temp_col is None:
            temp_col = col
        if "dew" in name and dew_col is None:
            dew_col = col
        if "press" in name and press_col is None:
            press_col = col
        if ("alt" in name or "height" in name) and alt_col is None:
            alt_col = col

    # Fallbacks
    if temp_col is None and len(df.columns) >= 1:
        temp_col = df.columns[0]
    if dew_col is None and len(df.columns) >= 2:
        dew_col = df.columns[1]
    if press_col is None and len(df.columns) >= 3:
        press_col = df.columns[2]

    st.markdown("### 🔧 Detected columns")
    col_map1, col_map2, col_map3, col_map4 = st.columns(4)
    with col_map1:
        temp_col = st.selectbox("Temperature (°C)", df.columns, index=list(df.columns).index(temp_col) if temp_col in df.columns else 0)
    with col_map2:
        dew_col = st.selectbox("Dew Point (°C)", df.columns, index=list(df.columns).index(dew_col) if dew_col in df.columns else 0)
    with col_map3:
        press_col = st.selectbox("Pressure (hPa)", df.columns, index=list(df.columns).index(press_col) if press_col in df.columns else 0)
    with col_map4:
        alt_col = st.selectbox("Altitude (optional, m)", ["(None)"] + list(df.columns),
                               index=(["(None)"] + list(df.columns)).index(alt_col) if alt_col in df.columns else 0)

    st.markdown("---")

    # Prepare profile
    prof = df[[temp_col, dew_col, press_col]].copy()
    prof[temp_col] = pd.to_numeric(prof[temp_col], errors="coerce")
    prof[dew_col] = pd.to_numeric(prof[dew_col], errors="coerce")
    prof[press_col] = pd.to_numeric(prof[press_col], errors="coerce")
    prof = prof.dropna()

    if prof.empty:
        st.error("No valid numeric data found in selected columns. Check mapping.")
    else:
        # Sort by pressure (surface to top)
        prof = prof.sort_values(by=press_col, ascending=False)

        P = prof[press_col].values * units.hectopascal
        T = prof[temp_col].values * units.degC
        Td = prof[dew_col].values * units.degC

        try:
            # ------- Compute indices -------
            K = k_index(P, T, Td)
            LI = lifted_index(P, T, Td)
            SI = showalter_index(P, T, Td)

            k_val = float(K.m)
            li_val = float(LI.m)
            si_val = float(SI.m)

            # Final logic
            if (k_val >= 35) or (li_val < -6) or (si_val < -3):
                final_text = "🌩️ High chance of thunderstorms"
                final_color = "#b91c1c"
            elif (25 <= k_val < 35) or (-6 <= li_val < -3) or (-3 <= si_val < 1):
                final_text = "⛈️ Moderate chance of thunderstorms"
                final_color = "#ca8a04"
            else:
                final_text = "🌤️ Low chance of thunderstorms"
                final_color = "#15803d"

            # ------- Top cards -------
            top_col1, top_col2 = st.columns([2, 3])

            with top_col1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("#### 🌩️ Overall Thunderstorm Assessment")
                st.markdown(f"<p style='font-size:20px; font-weight:600; color:{final_color};'>{final_text}</p>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with top_col2:
                c1, c2, c3 = st.columns(3)
                c1.metric("K-Index", f"{k_val:.1f}")
                c2.metric("Lifted Index (LI)", f"{li_val:.1f}")
                c3.metric("Showalter Index (SI)", f"{si_val:.1f}")

            st.markdown("")

            # ------- Detailed textual interpretation -------
            st.markdown("### 📝 Interpretation")
            # K
            if k_val < 20:
                k_cat = "Very low thunderstorm potential"
            elif 20 <= k_val < 25:
                k_cat = "Weak thunderstorm potential"
            elif 25 <= k_val < 35:
                k_cat = "Moderate thunderstorm potential"
            else:
                k_cat = "High thunderstorm potential"
            st.write(f"- **K-Index ({k_val:.1f})** → {k_cat}")

            # LI
            if li_val > 0:
                li_cat = "Stable atmosphere"
            elif -3 <= li_val <= 0:
                li_cat = "Slightly unstable"
            elif -6 <= li_val < -3:
                li_cat = "Moderately unstable"
            else:
                li_cat = "Strongly unstable (favourable for deep convection)"
            st.write(f"- **Lifted Index ({li_val:.1f})** → {li_cat}")

            # SI
            if si_val > 3:
                si_cat = "Stable"
            elif 1 <= si_val <= 3:
                si_cat = "Weakly unstable"
            elif -3 <= si_val < 1:
                si_cat = "Moderately unstable"
            else:
                si_cat = "Strongly unstable"
            st.write(f"- **Showalter Index ({si_val:.1f})** → {si_cat}")

            st.markdown("---")

            # ------- PLOTS SECTION -------
            st.markdown("### 📉 Vertical Profiles & Indices")

            plot_col1, plot_col2 = st.columns(2)

            # 1) T & Td vs Pressure
            with plot_col1:
                st.markdown("#### Temperature & Dew Point vs Pressure")
                plot_df = pd.DataFrame({
                    "Pressure (hPa)": prof[press_col].values,
                    "Temperature (°C)": prof[temp_col].values,
                    "Dew Point (°C)": prof[dew_col].values,
                })

                # Melt for Altair
                plot_long = plot_df.melt(id_vars="Pressure (hPa)", var_name="Variable", value_name="Value")

                chart = (
                    alt.Chart(plot_long)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("Value:Q", title="Temperature / Dew Point (°C)"),
                        y=alt.Y("Pressure (hPa):Q", sort="descending"),
                        color="Variable:N",
                        tooltip=["Pressure (hPa)", "Variable", "Value"]
                    )
                    .properties(height=350)
                )

                st.altair_chart(chart, use_container_width=True)

            # 2) Bar chart for indices
            with plot_col2:
                st.markdown("#### Indices Summary")
                idx_df = pd.DataFrame({
                    "Index": ["K-Index", "Lifted Index", "Showalter Index"],
                    "Value": [k_val, li_val, si_val]
                })

                idx_chart = (
                    alt.Chart(idx_df)
                    .mark_bar()
                    .encode(
                        x=alt.X("Index:N", title=""),
                        y=alt.Y("Value:Q"),
                        tooltip=["Index", "Value"]
                    )
                    .properties(height=350)
                )

                st.altair_chart(idx_chart, use_container_width=True)

            # ------- Optional altitude profile -------
            if alt_col != "(None)" and alt_col in df.columns:
                st.markdown("### 🗺️ Altitude vs Temperature (Optional)")
                alt_prof = df[[alt_col, temp_col]].copy()
                alt_prof[alt_col] = pd.to_numeric(alt_prof[alt_col], errors="coerce")
                alt_prof[temp_col] = pd.to_numeric(alt_prof[temp_col], errors="coerce")
                alt_prof = alt_prof.dropna()

                if not alt_prof.empty:
                    alt_chart = (
                        alt.Chart(alt_prof)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X(alt_col, title="Altitude"),
                            y=alt.Y(temp_col, title="Temperature (°C)"),
                            tooltip=[alt_col, temp_col]
                        )
                        .properties(height=300)
                    )
                    st.altair_chart(alt_chart, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error calculating indices: {e}")

else:
    st.info("👆 Please upload your STA / sounding file from the sidebar to begin.")
