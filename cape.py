import streamlit as st
import pandas as pd
import numpy as np
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
st.markdown(
    '<p class="sub">Upload your STA / sounding file and get K-Index, '
    'Lifted Index, Showalter Index and a final thunderstorm assessment.</p>',
    unsafe_allow_html=True
)

# ------------------- SIDEBAR -------------------
with st.sidebar:
    st.header("📂 Upload Data")
    uploaded_file = st.file_uploader(
        "Upload your STA file (.xls/.xlsx/.csv)",
        type=["xls", "xlsx", "csv"]
    )
    st.markdown("---")
    st.markdown("**Typical columns:**")
    st.markdown("- Temperature")
    st.markdown("- Dew Point")
    st.markdown("- Pressure")

# ------------------- MAIN LOGIC -------------------
if uploaded_file is not None:

    # Read file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("✅ File uploaded successfully!")

    with st.expander("📄 Preview data (top 10 rows)"):
        st.dataframe(df.head(10), use_container_width=True)

    # -------- Auto-detect columns --------
    temp_col = dew_col = press_col = alt_col = None

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

    if temp_col is None:
        temp_col = df.columns[0]
    if dew_col is None and len(df.columns) > 1:
        dew_col = df.columns[1]
    if press_col is None and len(df.columns) > 2:
        press_col = df.columns[2]

    # -------- Column selection --------
    st.markdown("### 🔧 Detected Columns")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        temp_col = st.selectbox("Temperature (°C)", df.columns,
                                index=df.columns.get_loc(temp_col))
    with c2:
        dew_col = st.selectbox("Dew Point (°C)", df.columns,
                               index=df.columns.get_loc(dew_col))
    with c3:
        press_col = st.selectbox("Pressure (hPa)", df.columns,
                                 index=df.columns.get_loc(press_col))
    with c4:
        alt_col = st.selectbox(
            "Altitude (optional)",
            ["(None)"] + list(df.columns),
            index=0
        )

    st.markdown("---")

    # -------- Prepare sounding profile --------
    prof = df[[temp_col, dew_col, press_col]].copy()
    prof[temp_col] = pd.to_numeric(prof[temp_col], errors="coerce")
    prof[dew_col] = pd.to_numeric(prof[dew_col], errors="coerce")
    prof[press_col] = pd.to_numeric(prof[press_col], errors="coerce")
    prof.dropna(inplace=True)

    if prof.empty:
        st.error("❌ No valid numeric data found.")
        st.stop()

    # Sort from surface to top
    prof = prof.sort_values(by=press_col, ascending=False)

    P = prof[press_col].values * units.hectopascal
    T = prof[temp_col].values * units.degC
    Td = prof[dew_col].values * units.degC

    try:
        # -------- Calculate indices --------
        K = k_index(P, T, Td)
        LI = lifted_index(P, T, Td)
        SI = showalter_index(P, T, Td)

        k_val = float(np.nanmean(K.m))
        li_val = float(np.nanmean(LI.m))
        si_val = float(np.nanmean(SI.m))

        # -------- Final assessment --------
        if (k_val >= 35) or (li_val < -6) or (si_val < -3):
            final_text = "🌩️ High chance of thunderstorms"
            final_color = "#b91c1c"
        elif (25 <= k_val < 35) or (-6 <= li_val < -3) or (-3 <= si_val < 1):
            final_text = "⛈️ Moderate chance of thunderstorms"
            final_color = "#ca8a04"
        else:
            final_text = "🌤️ Low chance of thunderstorms"
            final_color = "#15803d"

        # -------- Display results --------
        colA, colB = st.columns([2, 3])

        with colA:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("#### 🌩️ Thunderstorm Assessment")
            st.markdown(
                f"<p style='font-size:20px;font-weight:600;color:{final_color};'>"
                f"{final_text}</p>",
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with colB:
            x1, x2, x3 = st.columns(3)
            x1.metric("K-Index", f"{k_val:.1f}")
            x2.metric("Lifted Index", f"{li_val:.1f}")
            x3.metric("Showalter Index", f"{si_val:.1f}")

        st.markdown("---")
        st.markdown("### 📈 Sounding & Indices")

        # -------- GRAPH 1: Temp & Dew Point vs Pressure --------
        plot_df = pd.DataFrame({
            "Pressure (hPa)": prof[press_col].values,
            "Temperature (°C)": prof[temp_col].values,
            "Dew Point (°C)": prof[dew_col].values
        })

        plot_long = plot_df.melt(
            id_vars="Pressure (hPa)",
            var_name="Variable",
            value_name="Value"
        )

        temp_chart = (
            alt.Chart(plot_long)
            .mark_line(point=True)
            .encode(
                x="Value:Q",
                y=alt.Y("Pressure (hPa):Q", sort="descending"),
                color="Variable:N",
                tooltip=["Pressure (hPa)", "Variable", "Value"]
            )
            .properties(height=350)
        )

        # -------- GRAPH 2: Indices bar chart --------
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

        # -------- Display both graphs side-by-side --------
        g1, g2 = st.columns(2)
        with g1:
            st.altair_chart(temp_chart, use_container_width=True)
        with g2:
            st.altair_chart(idx_chart, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error calculating indices: {e}")

else:
    st.info("👆 Please upload your STA / sounding file to begin.")

