from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import pandas as pd
import openai
from sentence_transformers import SentenceTransformer, util
import io
from dotenv import load_dotenv


app = Flask(__name__)
CORS(app) 

# Load the pre-trained model
# model = SentenceTransformer('all-MiniLM-L6-v2')
load_dotenv()

# Access the OpenAI API key from the environment
openai.api_key = os.getenv('OPENAI_API_KEY')

# Endpoint for file upload and processing
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Get the uploaded file from the request
        file = request.files['file']
        if not file:
            return jsonify({"error": "No file provided"}), 400

        # Read the uploaded Excel file into a DataFrame
        df = pd.read_excel(file)

        # Check for required columns
        required_columns = ['PROTEIN %', 'PDCAAS']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({"error": f"Missing required columns: {', '.join(missing_columns)}"}), 400

        # Extract the first column and join rows into a comma-separated string
        first_column_values = df.iloc[:, 0].dropna().astype(str)  # Drop NaNs and ensure string type
        result_string = ', '.join(first_column_values)

        # Define the prompt for OpenAI
        p = (
            "Provide the FDA RACC values from site "
            "[https://www.canada.ca/en/health-canada/services/technical-documents-labelling-requirements/nutrition-labelling-table-reference-amounts-food.html] "
            "in grams for the following comma-separated product categories in a markdown format with two columns: "
            "'Product Category' and 'RACC Value (grams)'. Ensure the response is formatted as a markdown table. "
            "Consider the semantic meaning of each product, including preparation type (e.g., dry, raw, cooked, baked):"
        )
        prompt = p + "[" + result_string + "]"

        # Make the API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0  # Lower temperature for more deterministic output
        )

        # Extract the content of the response
        table_text = response['choices'][0]['message']['content']

        # Parse the response into a DataFrame
        if "|" in table_text:  # Check if the table is Markdown formatted
            table_df = pd.read_csv(io.StringIO(table_text), sep="|", skipinitialspace=True).iloc[1:, 1:-1]
            table_df.columns = table_df.iloc[0]  # Assign the first row as column headers
            table_df = table_df[1:]  # Remove the header row from the data
        else:
            return jsonify({"error": "Failed to parse the OpenAI response as a table."}), 500

        # Add Reference Amount to the original DataFrame
        table_df.columns = ['Product Category', 'Reference Amount']
        table_df = table_df.reset_index(drop=True)
        df['Reference Amount'] = table_df['Reference Amount']

        # Define a function to calculate protein labels
        def calculate_label(row, flag):
            # Convert relevant columns to numeric, handling errors
            protein_percent = pd.to_numeric(row['PROTEIN %'], errors='coerce')
            reference_amount = pd.to_numeric(row['Reference Amount'], errors='coerce')
            if flag ==0:
                pdcaas = pd.to_numeric(row['PDCAAS'], errors='coerce')
            elif flag == 1:
                pdcaas = pd.to_numeric(row['IVPDCAAS'], errors='coerce')
            

            # Check if any of the values are NaN after conversion
            if pd.isna(protein_percent) or pd.isna(reference_amount) or pd.isna(pdcaas):
                final_result = float('nan')  # Assign NaN if any value is invalid
            else:
                final_result = (protein_percent / 100) * reference_amount * (pdcaas / 100)

            # Determine protein label
            if final_result > 10:
                label = "Excellent Source of Protein"
            elif 5 <= final_result <= 10:
                label = "Good Source of Protein"
            elif final_result > 5:
                label = "Content Claim Possible"
            else:
                label = "No Claim"

            return pd.Series([final_result, label])

        # Apply the calculation to the DataFrame
        df[['Calculated Value(PDCAAS)', 'Protein Label(PDCAAS)']] = df.apply(calculate_label, axis=1, flag = 0)
        df[['Calculated Value(IVPDCAAS)', 'Protein Label(IVPDCAAS)']] = df.apply(calculate_label, axis=1, flag = 1)

        # Save the resulting DataFrame to an Excel file
        df=df.drop('Reference Amount',axis=1)
        output_file = os.path.join(os.getcwd(), "Final_Labelled_table.xlsx")
        df.to_excel(output_file, index=False)

        # Send the file back as a response
        return send_file(output_file, as_attachment=True)

    except Exception as e:
        # print(f"Error: {str(e)}")  # Log the error
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
