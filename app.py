from flask import Flask, request, jsonify
import re
from tokenizer import TextChunker

app = Flask(__name__)

# Create a TextProcessor instance with the required regex
regex = re.compile(r'\b\w+\b')  # Example regex to match words
text_processor = TextChunker()

@app.route('/tokenizer', methods=['POST'])
def process_data():
    data = request.json
    input_data = data.get('input_data')
    input_type = data.get('input_type')
    
    if not input_data or not input_type:
        return jsonify({"error": "Missing input data or input type"}), 400
    
    response = text_processor.process(input_data, input_type)
    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=True)
