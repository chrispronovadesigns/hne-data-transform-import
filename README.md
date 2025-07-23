# WooCommerce Import Formatter for WebToffee

This Streamlit app transforms product data from an Excel file into a WebToffee-compatible CSV for WooCommerce import.

Workflow:
Upload an Excel file with product and variation data.
Select relevant columns (SKU, Product Name, Categories).
Configure which columns are used as attributes, which affect SKU (variation), and which are visible on the Additional Info section.
The app generates a CSV where:
Parent (variable) rows have attribute_data columns set to 0|0|1 or 0|1|1 (visibility flag).
Variation (child) rows have attribute_data columns set to the available value(s) (pipe-separated) for attributes that affect SKU and have fewer options than the parent; all other fields are blank.
All attribute values are pipe-separated.
regular_price is set to 0 for all rows.

Output columns:
attribute:pa_{slug}, attribute_data:pa_{slug}, attribute_default:pa_{slug}, attribute_variation:pa_{slug}
Standard WooCommerce/WebToffee columns (sku, post_title, etc.)

How to run: python -m streamlit run hne-data-import-transform.py\
