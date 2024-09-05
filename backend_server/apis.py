# new
from flask import Flask, request, jsonify
from flask_cors import CORS

from openai import OpenAI

class DagCreate():
    def __init__(self):
        self.client = OpenAI(
          api_key="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",  # this is also the default, it can be omitted
        )

    def get_python_code(self, prompt):
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        print(completion)
        res = completion.choices[0].message.content.split("```python\n")
        result = res[1].split("```")
        return result[0]

    def save_file(self, python_code, filename):
        filepath = f"/app/dags/{filename}.py"
        with open(filepath, "w") as file:
            file.write(python_code)

    def create_dag(self, prompt, dag_name):
        python_code = self.get_python_code(prompt)
        self.save_file(python_code, dag_name)

app = Flask(__name__)
CORS(app)

@app.route('/test', methods=['GET', 'POST'])
def system_analysis():
    pass

@app.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    data = request.get_json()
    prompt = data.get('prompt')
    dag_name = data.get('filename')

    return f"Server is working: {prompt}\n{dag_name}", 200

@app.route('/create_dag', methods=['POST'])
def create_dag():
    data = request.get_json()
    prompt = data.get('prompt')
    dag_name = data.get('filename')
    if not prompt or not dag_name:
        return jsonify({"error": "Missing required fields: 'prompt' and 'filename'"}), 400
    try:
        d = DagCreate()
        d.create_dag(prompt, dag_name)
        return jsonify({"message": "DAG created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True)