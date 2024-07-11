import pandas as pd
import string

def format_currency(value):
    """
    Format a number as a currency string with commas as thousand separators and the default currency symbol 'TSh'.

    Parameters:
    value (float): The numeric value to be formatted.

    Returns:
    str: The formatted currency string.
    """
    currency_symbol = 'TSh'

    # Format the number with commas as thousand separators and two decimal places
    formatted_number = f"{value:,.2f}"

    # Add the currency symbol
    formatted_currency = f"{currency_symbol} {formatted_number}"

    return formatted_currency


def normalize_lender_data(lender_df):
    """
    Normalize the lender data in a DataFrame.

    This function converts the 'created_at' column to a datetime format (day.month.year),
    converts the 'credit' and 'debit' columns to numeric types, coercing any errors,
    and adds a 'normalized_description' column which is the 'description' column in
    lower case, without punctuation marks and spaces.

    Parameters:
    - lender_df (pd.DataFrame): The DataFrame containing lender data. It must have
    'created_at', 'credit', 'debit', and 'description' columns.

    Returns:
    - pd.DataFrame: The normalized DataFrame with the specified columns converted.
    """
    # Normalize 'created_at' date format to dd.mm.yyyy
    lender_df['created_at'] = pd.to_datetime(lender_df['created_at']).dt.strftime('%d.%m.%Y')

    # Convert 'credit' and 'debit' columns to numeric
    lender_df['credit'] = pd.to_numeric(lender_df['credit'], errors='coerce')
    lender_df['debit'] = pd.to_numeric(lender_df['debit'], errors='coerce')

    # Normalize 'description' column
    lender_df['normalized_description'] = lender_df['description'].apply(lambda x: ''.join(e for e in x.lower() if e.isalnum()))

    return lender_df



def normalize_bank_data(bank_df):
    """
    Normalize the bank data in a DataFrame.

    This function converts the 'Posting Date' and 'Value Date' columns to a datetime format (day.month.year),
    converts the 'Debit' and 'Credit' columns to numeric types, coercing any errors,
    and adds a 'normalized_description' column which is the 'Details' column in
    lower case, without punctuation marks and spaces.

    Parameters:
    - bank_df (pd.DataFrame): The DataFrame containing bank data. It must have
    'Posting Date', 'Value Date', 'Debit', 'Credit', and 'Details' columns.

    Returns:
    - pd.DataFrame: The normalized DataFrame with the specified columns converted.
    """

    def parse_date(date_str):
        # Attempt to parse the date string with the expected format
        try:
            return pd.to_datetime(date_str, format='%d.%m.%Y %H:%M:%S').strftime('%d.%m.%Y')
        except ValueError:
            # If parsing fails, try to parse it with a more flexible approach
            try:
                return pd.to_datetime(date_str, dayfirst=True).strftime('%d.%m.%Y')
            except ValueError:
                # If all parsing attempts fail, return the original string
                return date_str

    # Normalize 'Posting Date' and 'Value Date' date format to dd.mm.yyyy
    bank_df['Posting Date'] = bank_df['Posting Date'].apply(parse_date)
    bank_df['Value Date'] = bank_df['Value Date'].apply(parse_date)

    # Ensure that 'Debit' and 'Credit' columns are strings
    bank_df['Debit'] = bank_df['Debit'].astype(str).str.replace(',', '').astype(float)
    bank_df['Credit'] = bank_df['Credit'].astype(str).str.replace(',', '').astype(float)

    # Normalizing other relevant columns if needed
    bank_df['Details'] = bank_df['Details'].astype(str)

    # Normalize 'Details' column
    bank_df['normalized_description'] = bank_df['Details'].apply(lambda x: ''.join(e for e in x.lower() if e.isalnum()))

    return bank_df[bank_df['normalized_description'].str.contains('ramani') & (bank_df['Credit'] == 0)]



def get_lender_stats(lender_statement):
    """
    Get Dataset Stats
    input: lender_statement (pd.DataFrame)
    output: dict
    """
    results = {}
    credit_debit = {}

    # Total number of records
    results['records'] = len(lender_statement)
    results['matched'] = len(lender_statement[lender_statement['ismatched'] == 'checked'])
    results['unmatched'] = len(lender_statement[lender_statement['ismatched'] == 'Not Checked'])
    results['PoP'] = len(lender_statement[lender_statement['POP'] != 'No PoP Provided'])
    results['no_PoP'] = len(lender_statement[lender_statement['POP'] == 'No PoP Provided'])
    total_credit = lender_statement[lender_statement['credit'].notnull()]['credit'].sum()
    total_debit = lender_statement[lender_statement['debit'].notnull()]['debit'].sum()

    # Format as currency
    credit_debit['credit_amount'] = format_currency(total_credit)
    credit_debit['debit_amount'] = format_currency(total_debit)

    return results, credit_debit


def get_bank_stats(bank_statement):
    """
    Get Dataset Stats
    input: bank_statement (pd.DataFrame)
    output: dict
    """
    results = {}
    credit_debit = {}

    # Total number of records
    results['records'] = len(bank_statement)
    total_credit = bank_statement['Credit'].sum()
    total_debit = bank_statement['Debit'].sum()

    # Min - Max Posting Date
    results['From'] = bank_statement['Posting Date'].iloc[0]
    results['To'] = bank_statement['Posting Date'].iloc[-1]

    # Format as currency
    results['records'] = len(bank_statement)
    credit_debit['credit'] = format_currency(total_credit)
    credit_debit['debit'] = format_currency(total_debit)

    return results, credit_debit



def check_missing_from_lender(bank_statement, lender_statement):
    """
    Check if there are any records in the bank statement that are missing from the lender statement.

    Parameters:
    - bank_statement (pd.DataFrame): The bank statement DataFrame.
    - lender_statement (pd.DataFrame): The lender statement DataFrame.

    Returns:
    - pd.DataFrame: A DataFrame containing the records in the bank statement that are missing from the lender statement.
    """
    # Get the normalized descriptions from both DataFrames
    bank_descriptions = bank_statement['normalized_description']
    lender_descriptions = lender_statement['normalized_description']

    # Find the records in the bank statement that are missing from the lender statement
    missing_records = bank_statement[~bank_descriptions.isin(lender_descriptions)]

    return missing_records


def get_lender_df_by_column_and_value(column_name, value, lender_statement):
    """
    Get a subset of the lender statement DataFrame based on a column value.

    Parameters:
    - column_name (str): The name of the column to filter on.
    - value (str): The value to filter the column on.
    - lender_statement (pd.DataFrame): The lender statement DataFrame.

    Returns:
    - pd.DataFrame: A subset of the lender statement DataFrame where the specified column has the specified value.
    """
    return lender_statement[lender_statement[column_name] == value]