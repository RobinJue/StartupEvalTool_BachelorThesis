import pandas as pd
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_json_data(json_file_path):
    """
    Loads JSON data from a file and returns it as a list of dictionaries.
    
    Args:
        json_file_path (str): Path to the JSON file.
        
    Returns:
        list: The loaded JSON data as a list of dictionaries.
    """
    try:
        with open(json_file_path, "r", encoding="utf-8") as file:
            logger.info(f"Loaded JSON data from {json_file_path}")
            return json.load(file)
    except Exception as e:
        raise ValueError(f"Error loading JSON data: {e}")

def find_founding_year(data):
    """
    Finds the most common founding year from the JSON data.
    If there is a tie for the most common founding year, the earliest year is used.
    
    Args:
        data (list): The JSON data as a list of dictionaries.
        
    Returns:
        int: The founding year of the company.
    """
    try:
        # Extract all founding years from the JSON data
        founding_years = []
        for record in data:
            for year_data in record.values():
                if "Year founded" in year_data and year_data["Year founded"]:
                    founding_years.append(year_data["Year founded"])
        
        if not founding_years:
            logger.error("No founding year found in the JSON data.")
            raise ValueError("No founding year found in the JSON data.")
        
        # Count the frequency of each founding year
        year_counts = {}
        for year in founding_years:
            year_counts[year] = year_counts.get(year, 0) + 1
        
        # Find the most common founding year(s)
        max_count = max(year_counts.values())
        common_years = [year for year, count in year_counts.items() if count == max_count]
        
        # If there's a tie, return the earliest year
        logger.info(f"Found most common founding year: {min(common_years)}")
        return min(common_years)
    except Exception as e:
        raise ValueError(f"Error finding founding year: {e}")

def generate_table_outline():
    """
    Generate an empty table with predefined features/columns.
    Notice that we do NOT include 'Yr' here to avoid duplicates.
    
    Returns:
        pd.DataFrame: A pandas DataFrame representing the empty table.
    """
    columns = [
        # Removed "Yr" from here
        "Rev",             # Revenue
        "GP",              # Gross Profit
        "GP Marg",         # Gross Profit Margin
        "Op Inc",          # Operating Income
        "Op Exp",          # Operating Expenses
        "Op Marg",         # Operating Margin
        "Net Loss",        # Net Loss
        "Net Inc",         # Net Income
        "FCF",             # Free Cash Flow
        "Cust",            # Customers
        "Cust Gr",         # Customer Growth
        "Src Dt",          # Source Date
        "Src"              # Data Source
    ]
    
    # Create an empty DataFrame with the specified columns
    empty_table = pd.DataFrame(columns=columns)
    return empty_table

def populate_years(table, start_year):
    """
    Create a new DataFrame with 1 row for each year from start_year to the current year.
    Then copy over the columns from the 'table' outline, and add the 'Yr' column separately.
    
    Args:
        table (pd.DataFrame): The "outline" DataFrame with columns (no rows).
        start_year (int): The first year to populate.
        
    Returns:
        pd.DataFrame: A DataFrame with (current_year - start_year + 1) rows, and columns from the outline plus 'Yr'.
    """
    current_year = datetime.now().year
    years = list(range(start_year, current_year + 6))

    # Number of rows == number of years
    num_rows = len(years)
    
    # Create a new DataFrame with the same columns as table + 'Yr'
    new_columns = ["Yr"] + list(table.columns)
    new_table = pd.DataFrame(index=range(num_rows), columns=new_columns)
    
    # Fill in the 'Yr' column
    new_table["Yr"] = years
    
    # The rest of the columns are initially NaN / None
    # (table was empty but had the correct columns, so we've mirrored that structure)
    
    logger.info(f"Populated table with years from {start_year} to {years[-1]}")
    return new_table

def create_full_data_dict_sorted_by_year(json_data, start_year):
    """
    Create a dictionary where the keys are years from start_year to the current year,
    and the values are lists of all dictionary objects from that year in the JSON data,
    sorted by source date ("null" or no date first, then oldest to newest).
    
    Args:
        json_data (list): The JSON data as a list of dictionaries.
        start_year (int): The first year to include in the dictionary.
    
    Returns:
        dict: The full data dictionary sorted by year.
    """
    current_year = datetime.now().year
    full_data_dict = {year: [] for year in range(start_year, current_year + 6)}  # Initialize dictionary with empty lists
    
    # Populate the dictionary with data from the JSON
    for record in json_data:
        for year_str, details in record.items():
            # Safely convert to integer if possible
            try:
                year_int = int(year_str)
            except ValueError:
                logger.debug(f"No matching row for year {year} in the table, skipping.")
                continue  # Not found, skip
            
            if year_int in full_data_dict:
                full_data_dict[year_int].append(details)  # Append the details to the corresponding year

    # Sort the arrays for each year:
    for year in full_data_dict:
        full_data_dict[year] = sorted(
            full_data_dict[year],
            key=lambda x: (
                0 if not x.get("Source Date") or x["Source Date"].lower() == "null" else 1,
                datetime.strptime(x["Source Date"], "%B %d, %Y")
                if x.get("Source Date") and x["Source Date"].lower() != "null"
                else datetime.min
            )
        )
    
    logger.info(f"Created full data dictionary for years {start_year} to {current_year + 5}")
    return full_data_dict

def fill_table_with_data(table, full_data_dict):
    """
    Fill the given table with data from the full_data_dict.
    - 'table' must have a "Yr" column plus the columns from our outline.
    - Each key in 'full_data_dict' is a year, and the value is a list of records
      sorted from oldest to newest, so we apply them in ascending order
      so that later records override earlier ones with non-null values.
    """
    
    # Mapping from the JSON keys to the DataFrame columns
    mapping = {
        "Revenue": "Rev",
        "Gross Profit": "GP",
        "Gross Profit Margin": "GP Marg",
        "Operating Income": "Op Inc",
        "Operating Expenses": "Op Exp",
        "Operating Margin": "Op Marg",
        "Net Loss": "Net Loss",
        "Net Income": "Net Inc",
        "Free Cash Flow": "FCF",
        "Customers": "Cust",
        "Customer Growth": "Cust Gr",
        "Source Date": "Src Dt",
        "Data Source": "Src"
    }
    
    for year, records in full_data_dict.items():
        # Locate the row in 'table' that corresponds to this year
        # .loc[...] with a boolean Series will only work if 'table["Yr"]' is a Series of years
        row_indices = table.index[table["Yr"] == year]
        if len(row_indices) == 0:
            # Not found, skip
            continue
        row_idx = row_indices[0]  # we only expect one row per year

        # Apply each record in ascending order (oldest first, newest last)
        for record in records:
            for json_key, df_col in mapping.items():
                if json_key in record and record[json_key] is not None:
                    logger.debug(f"Updating {df_col} for year {year} with value: {record[json_key]}")
                    table.at[row_idx, df_col] = record[json_key]
    
    return table

def start(json_file_path):
    """Entry point for table_generator."""
    logger.info("Loading JSON data...")
    try:
        json_data = load_json_data(json_file_path)
    except ValueError as e:
        print(f"Error: {e}")
        return None

    logger.info("Finding founding year...")
    try:
        founding_year = find_founding_year(json_data)
        print(f"Founding Year: {founding_year}")
    except ValueError as e:
        print(f"Error: {e}")
        return None

    outline_table = generate_table_outline()
    table = populate_years(outline_table, founding_year)
    full_data_dict_sorted_by_year = create_full_data_dict_sorted_by_year(json_data, founding_year)
    table = fill_table_with_data(table, full_data_dict_sorted_by_year)

    print("Generated Table with Data:")
    print(table.to_markdown(index=False))
    logger.info("Table generation complete.")
    return table