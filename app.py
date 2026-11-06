import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import requests
from dotenv import load_dotenv

# page config
st.set_page_config(page_title="OBD-II Log Analyzer", layout="wide")

load_dotenv()
api_key = os.getenv("CLAUDE_KEY")

st.title("OBD-II Log Analyzer")
st.markdown("Upload a raw CSV file. This tool cleans the data, plots the RPM/Temperature correlation, and drafts a quick diagnostic report.")

uploaded_file = st.file_uploader("Upload Log File (CSV)", type=["csv"])

if uploaded_file is not None:
    # reading and cleaning
    df = pd.read_csv(uploaded_file, comment='#', na_values=["NaN", "null", ""], encoding='latin-1')
    
    # data integrity
    st.subheader("Review")
    total_cells = df.size
    missing_cells = df.isna().sum().sum()
    integrity_score = 100 - ((missing_cells / total_cells) * 100)
    
    col1, col2 = st.columns(2)
    with col1:
        if integrity_score >= 95.0:
            st.success(f"Data Integrity: {integrity_score:.1f}% (Clean CAN bus feed)")
        elif integrity_score >= 90.0:
            st.warning(f"Data Integrity: {integrity_score:.1f}% (Minor packet loss detected)")
        else:
            st.error(f"Data Integrity: {integrity_score:.1f}% (Critical data loss on CAN bus)")
            
    with col2:
        st.metric("Total Rows Processed", len(df))

    # # highlighting
    st.subheader("Raw CSV File")
    st.markdown("Missing packets are highlighted in **dark red**.")
    
    def highlight_missing(val):
        if pd.isna(val):
            return 'background-color: #4a1c1c; color: white'
        return ''
        
    st.dataframe(df.style.map(highlight_missing), height=250, use_container_width=True)
    
    # plotly graph
    st.subheader("Telemetry Graph")
    
    # 2 y-axes
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # RPM (left)
    fig.add_trace(
        go.Scatter(x=df['Timestamp'], y=df['Engine RPM (rpm)'], name="Engine RPM", line=dict(color="blue", width=1)),
        secondary_y=False,
    )

    # Coolant Temp (right)
    fig.add_trace(
        go.Scatter(x=df['Timestamp'], y=df['Coolant Temp (°C)'], name="Coolant Temp (°C)", line=dict(color="red", width=2)),
        secondary_y=True,
    )

    fig.update_layout(
        title_text="Engine RPM vs. Coolant Temperature",
        xaxis_title="Timestamp",
        plot_bgcolor="rgba(0,0,0,0)", 
        hovermode="x unified"
    )
    
    fig.update_yaxes(title_text="Engine RPM", secondary_y=False)
    fig.update_yaxes(title_text="Temperature (°C)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    # diagnostic with the help of AI
    st.subheader("Diagnosis")
    st.markdown("Generate a brief diagnostic summary and recommended next steps for the mechanics.")

    if st.button("Generate Diagnosis", type="primary"):
        if not api_key:
            st.error("API Key not found in .env file. Please check your setup.")
        else:
            with st.spinner("Isolating anomalies and querying Claude AI..."):
                # RAG FILTERING: isolate only the broken data
                # grabbing rows where Temp > 100 OR Temp < 0 (the -99 glitch)
                anomaly_df = df[(df['Coolant Temp (°C)'] > 100.0) | (df['Coolant Temp (°C)'] < 0)]
                
                # converting only the bad data to a CSV string
                anomaly_csv = anomaly_df.to_csv(index=False)
                
                # prompt
                system_prompt = """
                You are an automotive diagnostic assistant analyzing filtered OBD-II telemetry data from a test drive. 
                Your job is to read the CSV anomalies provided and generate a concise, actionable maintenance ticket.
                
                STRICT RULES & EDGE CASES:
                1. Data Glitches: If you see temperatures of -99.0, 'NaN', or blank fields, diagnose them as sensor dropouts, electrical shorts, or CAN bus packet loss. Do not treat them as literal physical temperatures.
                2. No Conversational Filler: Output ONLY the requested format. Do not say "Here is the ticket", "Based on the data", or add any introductions or conclusions.
                3. Conciseness: Keep the Diagnostic Summary to a maximum of 2 sentences. Be direct and technical.
                4. Empty Data: If the provided data contains no values, output exactly: "Status: No anomalies detected in the provided timeframe."
                
                Format your response EXACTLY like this (include the bolding):
                **Severity Level:** [CRITICAL / HIGH / WARNING]
                **Suspected Component:** [Name of the failing car part or sensor]
                **Diagnostic Summary:** [1-2 sentences explaining the correlation between RPM, Load, Temp, and Voltage]
                **Recommended Action:** [1-2 specific, actionable steps for the mechanics on the shop floor]
                """
                
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                payload = {
                    "model": "claude-haiku-5-5",
                    "max_tokens": 8192,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": f"Here is the anomalous telemetry data:\n\n{anomaly_csv}"}
                    ]
                }
                
                try:
                    response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        # safe parsing
                        report = "Error: Could not extract text from response."
                        for block in response_data.get('content', []):
                            if block.get('type') == 'text':
                                report = block.get('text')
                                break
                                
                        formatted_report = report.replace('\n', '\n\n')
                        st.info(formatted_report)
                    else:
                        st.error(f"API Error: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    st.error(f"Code Error: {e}")
