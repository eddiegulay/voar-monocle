import streamlit as st
import os
import pandas as pd
from controls import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Function to create directory if it doesn't exist
def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to save uploaded file to specified directory
def save_uploaded_file(uploaded_file, directory):
    create_directory(directory)
    with open(os.path.join(directory, uploaded_file.name), "wb") as f:
        f.write(uploaded_file.getbuffer())
    return os.path.join(directory, uploaded_file.name)

def display_metrics(title, stats):
    if title != "":
        st.subheader(title)
    cols = st.columns(len(stats))
    for col, (metric, value) in zip(cols, stats.items()):
        col.metric(metric, value)


def process_large_csv(file_path, chunk_size=10000, needle=None):
    """Read and process large CSV file in chunks."""
    chunks = []
    try:
        for chunk in pd.read_csv(file_path, chunksize=chunk_size, encoding='utf-8'):
            chunk = normalize_bank_data(bank_df=chunk, needle=needle)
            chunks.append(chunk)
        return pd.concat(chunks, ignore_index=True)
    except UnicodeDecodeError:
        logger.error("Failed to decode file with utf-8 encoding, trying with latin encoding")
        for chunk in pd.read_csv(file_path, chunksize=chunk_size, encoding='latin'):
            chunk = normalize_bank_data(chunk, needle=needle)
            chunks.append(chunk)
            new_df = pd.concat(chunks, ignore_index=True)
        return new_df


def main():
    st.title("🧐 Flit Monocle")
    st.write("Cross company statement recon.")
    st.write("---")

    # Define directories for uploaded files
    crdb_directory = "uploaded_files/crdb"
    lending_directory = "uploaded_files/lending"

    # Check if files already exist
    crdb_files = os.listdir(crdb_directory) if os.path.exists(crdb_directory) else []
    lending_files = os.listdir(lending_directory) if os.path.exists(lending_directory) else []

    # Initialize variables
    crdb_file_path = None
    lending_file_path = None

    # Sidebar with file upload widgets
    st.sidebar.title("Upload Files")
    crdb_file = st.sidebar.file_uploader("Upload CRDB Bank Statement CSV", type="csv")
    lending_file = st.sidebar.file_uploader("Upload Lending Company Payment Document CSV", type="csv")

    if crdb_file:
        crdb_file_path = save_uploaded_file(crdb_file, crdb_directory)
    elif crdb_files:
        crdb_file_path = os.path.join(crdb_directory, crdb_files[0])

    if lending_file:
        lending_file_path = save_uploaded_file(lending_file, lending_directory)
    elif lending_files:
        lending_file_path = os.path.join(lending_directory, lending_files[0])

    # If files are available, process them
    if crdb_file_path and lending_file_path:
        bank_statement = process_large_csv(crdb_file_path, needle="ramani")
        lending_statement = pd.read_csv(lending_file_path)

        # Normalize data
        bank_statement = normalize_bank_data(bank_statement)
        lending_statement = normalize_lender_data(lending_statement)

        # Fill NaN in ismatched with 'Not Checked'
        try:
            lending_statement['ismatched'] = lending_statement['ismatched'].fillna('Not Checked')
            lending_statement['POP'] = lending_statement['POP'].fillna('No PoP Provided')
        except KeyError:
            logger.info("No ismatched or POP columns in lending statement")

        # Get File stats
        bank_stats, bank_credit_debit = get_bank_stats(bank_statement)
        lender_stats, credit_debit = get_lender_stats(lending_statement)

        # Display Bank Statement Stats
        display_metrics("Bank Statement Stats", bank_stats)
        display_metrics("", bank_credit_debit)

        # Display Lending Company Payment Document Stats
        display_metrics("Airtable Document Stats", lender_stats)
        display_metrics("", credit_debit)
        st.write("---")

        # check if there are missing PoPs
        if lender_stats['no_PoP'] > 0:
            st.subheader("🧾 Records missing Proof of Payment (airtable):")
            st.write(get_lender_df_by_column_and_value('POP', 'No PoP Provided', lending_statement))
            # total missing value
            total_missing_value = lending_statement[lending_statement['POP'] == 'No PoP Provided']['credit'].sum()
            total_missing_value = format_currency(total_missing_value)
            st.write(f"Total Missing Value (sent to lender): {total_missing_value}")

        # check if there are unmatched records
        if lender_stats['unmatched'] > 0:
            st.subheader("❌ Unmatched Records (airtable):")
            st.write(get_lender_df_by_column_and_value('ismatched', 'Not Checked', lending_statement))
            # total unmatched value
            total_unmatched_value = lending_statement[lending_statement['ismatched'] == 'Not Checked']['credit'].sum()
            total_unmatched_value = format_currency(total_unmatched_value)
            st.write(f"Total Unmatched Value: {total_unmatched_value}")

        st.write("---")
        # check missing from lender
        missing_from_lender, matching_records = check_missing_from_lender(bank_statement, lending_statement)
        if len(missing_from_lender) > 0:
            # Display missing from lender
            st.subheader("⚠️ Records missing from Airtable:")
            st.write("Total Missing Records: ", len(missing_from_lender))
            st.write(missing_from_lender.drop(columns=['normalized_description', 'Book Balance']))

            # total missing amount missing from lender
            total_missing_amount = missing_from_lender['Debit'].sum()
            total_missing_amount = format_currency(total_missing_amount)
            st.write(f"Total Missing Amount: {total_missing_amount}")

            # matching records
            st.subheader("✅ Matching Records (bank statement & airtable):")
            st.write("Total Matching Records: ", len(matching_records))
            st.write(matching_records)


            st.write("---")
            # total matching amount
            total_matching_amount = matching_records['Debit'].sum()
            total_matching_amount = format_currency(total_matching_amount)
            st.write(f"Total Matching Amount: {total_matching_amount}")
        else:
            st.info("No records missing from Airtable")


        st.write("---")
        st.subheader("All found transactions:")
        st.write(bank_statement)

    else:
        st.info("Please upload both CSV files to start reconciliation.")

if __name__ == "__main__":
    main()
