# WooCommerce Import Formatter for WebToffee
# How to run script: python -m streamlit run hne-data-import-transform.py

import pandas as pd
import streamlit as st
import io
from collections import defaultdict

st.title("WooCommerce Product Import Generator")
st.markdown("Upload an Excel file, pick the sheet, and download a WebToffee-ready CSV based on known variation attributes.")

uploaded_file = st.file_uploader("Upload Excel File", type=[".xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet = st.selectbox("Select sheet to use", xls.sheet_names)

    if sheet:
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
        df.columns = df.columns.str.strip()

        sku_column = st.selectbox("Select SKU column", df.columns)
        product_column = st.selectbox("Select Product Name column", df.columns)
        category_column = st.selectbox("Select Categories column", df.columns)
        
        # Add brand input
        brand_name = st.text_input("Enter brand name (will be used in SKUs and as a column)", "Enter Brand Name")

        # Dynamic attribute configuration
        st.subheader("Attribute Configuration")
        st.markdown("Select which columns should be used as attributes.")
        
        essential_cols = {sku_column, product_column, category_column, 'Price', 
                 'Short description', 'Description', 'Image URL', 'Regular price'}
        attribute_columns = [col for col in df.columns 
                    if col not in essential_cols 
                    and not pd.api.types.is_numeric_dtype(df[col])]    

        attribute_config = {}
        for col in attribute_columns:
            with st.expander(f"Configure: {col}", expanded=False):
                use_attr = st.checkbox(f"Use as attribute", key=f"use_{col}", value=True)
                if use_attr:
                    # Show preview of unique values
                    unique_vals = df[col].dropna().unique()
                    st.caption(f"Unique values ({len(unique_vals)}): {', '.join(map(str, unique_vals[:5]))}")
                    if len(unique_vals) > 5:
                        st.caption(f"... and {len(unique_vals) - 5} more")
                        
                    attribute_config[col] = {
                        "slug": col.lower().replace(" ", "-"),
                        "values": unique_vals
                    }

        st.markdown("Using the following variation attributes:")
        st.write(attribute_config)

        def clean_attr_values(values):
            return [str(v).replace(',', '|').replace(' ', '').strip() for v in values if pd.notna(v) and str(v).strip()]

        if st.button("Generate WebToffee Import File"):
            grouped = df.groupby(product_column)
            output_rows = []
            df['brand'] = brand_name

            for product_name, group in grouped:
                first_sku = group.iloc[0][sku_column]
                brand_prefix = brand_name.upper().replace(' ', '')
                parent_sku = f"{brand_prefix}-{first_sku}"
                base_data = {
                    'product_type': 'variable',
                    'post_type': 'product',
                    'post_title': f"{brand_name} {product_name}",
                    'brand': brand_name,
                    'sku': parent_sku,
                    'categories': group.iloc[0].get(category_column, ''),
                    'stock_status': 'instock',
                    'short_description': group.iloc[0].get('Short description', ''),
                    'description': group.iloc[0].get('Description', ''),
                    'images': group.iloc[0].get('Image URL', '')
                }
                if not attribute_config:
                    st.warning("No attributes configured. Please select at least one attribute to continue.")
                    st.stop()

                # Parent attributes
                for col, config in attribute_config.items():
                    if col in group.columns:
                        attr_values = clean_attr_values(group[col].dropna().unique())
                        if not attr_values:
                            continue
                        slug = config['slug']
                        joined_values = '|'.join(sorted(set(attr_values)))
                        base_data[f'attribute:pa_{slug}'] = joined_values
                        base_data[f'attribute_data:pa_{slug}'] = f"{joined_values.replace('|', '||')}|0|1"
                        base_data[f'attribute_variation:pa_{slug}'] = '1'
                        base_data[f'attribute_default:pa_{slug}'] = ''
                output_rows.append(base_data)

                # Variations
                for _, row in group.iterrows():
                    variation_data = {
                        'product_type': 'variation',
                        'post_type': 'product_variation',
                        'post_title': f"{product_name} - {row[sku_column]}",
                        'sku': row[sku_column],
                        'parent_sku': parent_sku,
                        'regular_price': '0',
                        'stock_status': 'instock',
                        'images': row.get('Image URL', '')
                    }
                    for col, config in attribute_config.items():
                        if col in group.columns and pd.notna(row[col]):
                            slug = config['slug']
                            parent_value = base_data.get(f'attribute:pa_{slug}', '')
                            parent_values = set(parent_value.split('|')) if parent_value else set()
                            mask = pd.Series(True, index=group.index)
                            for other_col in attribute_config:
                                if other_col != col and other_col in group.columns:
                                    mask &= (group[other_col] == row[other_col]) | pd.isna(group[other_col])
                            available_values = set(clean_attr_values(group.loc[mask, col].dropna().unique()))
                            if available_values and len(available_values) < len(parent_values):
                                variation_data[f'meta:attribute_pa_{slug}'] = '|'.join(sorted(available_values))
                    output_rows.append(variation_data)

            df_out = pd.DataFrame(output_rows)
            
            # Reorder columns to put important ones first
            column_order = [
                'product_type', 'post_type', 'post_title', 'sku', 'parent_sku',
                'regular_price', 'stock_status', 'categories', 'short_description',
                'description', 'images'
            ]

            # Add attribute columns in a logical order
            attr_columns = []
            for col, config in attribute_config.items():
                slug = config['slug']
                # Add standard attribute columns
                attr_columns.extend([
                    f'attribute:pa_{slug}',
                    f'attribute_data:pa_{slug}',
                    f'attribute_default:pa_{slug}',
                    f'attribute_variation:pa_{slug}',
                    f'meta:attribute_pa_{slug}'  # Add meta attribute column for each attribute
                ])

            # Combine all columns, removing duplicates and keeping order
            all_columns = column_order + [col for col in attr_columns if col not in column_order]
            # Ensure all columns exist in the DataFrame
            for col in all_columns:
                if col not in df_out.columns:
                    df_out[col] = ''
            
            # Reorder columns
            df_out = df_out[all_columns]
            
            # Generate CSV and create download button
            csv_data = df_out.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download WebToffee CSV",
                data=csv_data,
                file_name="webtoffee_import.csv",
                mime="text/csv"
            )