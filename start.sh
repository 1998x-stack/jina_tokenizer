python app.py
curl -X POST http://127.0.0.1:5000/tokenizer \
    -H "Content-Type: application/json" \
    -d '{"input_data": "./doc/Grimm.txt", "input_type": "file"}'