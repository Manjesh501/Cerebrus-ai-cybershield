import streamlit as st
import os
import time
import pandas as pd
from datetime import datetime
import sys
from run_batch_test import BatchProcessor, print_colored  # Import the correct components

st.set_page_config(
    page_title="Cerberus - AI Malware Analysis Shield",
    page_icon="🛡️",
    layout="wide"
)

def main():
    # Title and Description
    st.title("🛡️ Cerberus - AI Malware Analysis Shield")
    st.markdown("""
    An intelligent malware analysis framework providing multi-layered defense against modern cyber threats.
    
    ⚠️ **Warning**: Do not run malware analysis on your main system. Use a VM environment for dynamic and hybrid analysis.
    """)
    
    # Sidebar Configuration
    st.sidebar.header("Analysis Configuration")
    
    # File/Directory Selection
    st.sidebar.subheader("Select Files")
    uploaded_files = st.sidebar.file_uploader("Upload Files", accept_multiple_files=True)
    directory_path = st.sidebar.text_input("Or Enter Directory Path:")
    
    # Analysis Mode Selection
    analysis_mode = st.sidebar.radio(
        "Select Analysis Mode",
        ["Static analysis only (ML model)", 
         "Dynamic analysis only (Runtime behavior)", 
         "Hybrid analysis"],
        index=2
    )
    
    # Mode mapping
    mode_mapping = {
        "Static analysis only (ML model)": 1,
        "Dynamic analysis only (Runtime behavior)": 2,
        "Hybrid analysis": 3
    }
    
    # Custom Model Path
    custom_model = st.sidebar.text_input("Custom ML Model Path (optional):")
    
    # Output Directory
    output_dir = st.sidebar.text_input("Output Directory:", value="batch_results")
    
    # VirusTotal API Key
    vt_api_key = st.sidebar.text_input("VirusTotal API Key:", type="password")
    
    # Main Content Area
    if st.sidebar.button("Start Analysis"):
        if not (uploaded_files or directory_path):
            st.error("Please either upload files or provide a directory path.")
            return
            
        with st.spinner("Analyzing files..."):
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize analysis parameters
            files_to_analyze = []
            if uploaded_files:
                # Save uploaded files to temporary location
                for uploaded_file in uploaded_files:
                    temp_path = os.path.join("temp_uploads", uploaded_file.name)
                    os.makedirs("temp_uploads", exist_ok=True)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    files_to_analyze.append(temp_path)
            
            if directory_path:
                files_to_analyze.extend([
                    os.path.join(directory_path, f) 
                    for f in os.listdir(directory_path) 
                    if os.path.isfile(os.path.join(directory_path, f))
                ])
            
            # Set up environment variables if needed
            if vt_api_key:
                os.environ['VT_API_KEY'] = vt_api_key

            # Initialize the batch processor
            processor = BatchProcessor(output_dir=output_dir, model_path=custom_model)

            # Set analysis mode
            if mode_mapping[analysis_mode] == 1:
                processor.static_only = True
            elif mode_mapping[analysis_mode] == 2:
                processor.dynamic_only = True
            # Mode 3 (Hybrid) is default

            try:
                total_files = len(files_to_analyze)
                
                # Create timestamp for batch directory
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                batch_dir = os.path.join(output_dir, f"batch_{timestamp}")
                os.makedirs(batch_dir, exist_ok=True)
                
                # Create CSV file with headers
                csv_path = os.path.join(batch_dir, "results.csv")
                with open(csv_path, 'w', newline='') as f:
                    import csv
                    writer = csv.writer(f)
                    writer.writerow([
                        'File', 'Is Malware', 'Malware Type',
                        'Analysis Method', 'Processing Time'
                    ])
                
                results = []
                for idx, file_path in enumerate(files_to_analyze, 1):
                    # Update progress
                    progress = idx / total_files
                    progress_bar.progress(progress)
                    status_text.text(f"Analyzing {os.path.basename(file_path)}... ({idx}/{total_files})")
                    
                    # Process the file
                    result = processor._process_single_file(file_path, batch_dir)
                    results.append(result)
                    
                    # Determine analysis method based on mode
                    if mode_mapping[analysis_mode] == 1:
                        analysis_method = "Static"
                    elif mode_mapping[analysis_mode] == 2:
                        analysis_method = "Dynamic"
                    else:
                        analysis_method = "Hybrid"
                    
                    # Add to CSV
                    with open(csv_path, 'a', newline='') as f:
                        writer = csv.writer(f)
                        row = [
                            os.path.basename(file_path),
                            'MALWARE' if result.get('is_malware', False) else 'CLEAN',
                            result.get('malware_type', 'Unknown'),
                            analysis_method,
                            f"{result.get('processing_time', 0):.2f}s"
                        ]
                        writer.writerow(row)
                
                # Show results
                st.success("Analysis Complete!")
                
                # Display results from the CSV
                latest_batch = max([d for d in os.listdir(output_dir) if d.startswith("batch_")])
                results_path = os.path.join(output_dir, latest_batch, "results.csv")
                if os.path.exists(results_path):
                    results_df = pd.read_csv(results_path)
                    st.subheader("Analysis Results")
                    
                    # Apply custom formatting to the dataframe
                    st.dataframe(
                        results_df,
                        column_config={
                            "File": st.column_config.TextColumn("File Name"),
                            "Is Malware": st.column_config.TextColumn(
                                "Status",
                                help="Whether the file is classified as malware or clean"
                            ),
                            "Malware Type": st.column_config.TextColumn(
                                "Malware Type",
                                help="Type of malware if detected"
                            ),
                            "Analysis Method": st.column_config.TextColumn(
                                "Analysis Method",
                                help="Type of analysis performed"
                            ),
                            "Processing Time": st.column_config.TextColumn(
                                "Processing Time",
                                help="Time taken to analyze the file"
                            )
                        }
                    )
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Files", len(results_df))
                    with col2:
                        malware_count = len(results_df[results_df["Is Malware"] == "MALWARE"])
                        st.metric("Malware Detected", malware_count)
                    with col3:
                        clean_count = len(results_df[results_df["Is Malware"] == "CLEAN"])
                        st.metric("Clean Files", clean_count)
                    
                    # Download button for results
                    st.download_button(
                        "Download Results CSV",
                        results_df.to_csv(index=False),
                        "malware_analysis_results.csv",
                        "text/csv"
                    )
                
            except Exception as e:
                st.error(f"An error occurred during analysis: {str(e)}")
            
            finally:
                # Cleanup temporary files if any
                if uploaded_files and os.path.exists("temp_uploads"):
                    import shutil
                    shutil.rmtree("temp_uploads")

if __name__ == "__main__":
    main()
