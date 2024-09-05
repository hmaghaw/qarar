import os
from openai import OpenAI
import mysql.connector
from mysql.connector import Error
import json
class DBActions():
    def __init__(self):
        self.topic_id = None
        self.host = "localhost"
        self.user = "user"
        self.password = "password"
        self.database = "db"
        self.create_connection()
        self.client = OpenAI(
            api_key="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",
            # this is also the default, it can be omitted
        )

    def create_connection(self):
        self.connection = None
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.connection.cursor()

            print("Connection to MySQL DB successful")
        except Error as e:
            print(f"The error '{e}' occurred")

    def read_base_prompt(self, file_name):
        script_dir = os.path.dirname(__file__)
        # Define the path to the file
        file_path = os.path.join(script_dir, 'prompts', file_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            print("File Content:")
            print(content)
        except FileNotFoundError:
            print(f"The file {file_path} does not exist.")
        except IOError:
            print(f"An error occurred while reading the file {file_path}.")
        return content

    def check_topic_exists(self, topic_name):
        # SQL query to check if the topic already exists
        sql = "SELECT topic_id FROM topic WHERE topic_name = %s"
        try:
            self.cursor.execute(sql, (topic_name,))
            result = self.cursor.fetchone()
            if result:
                return result[0]  # Return the existing topic_id
            return None  # Topic does not exist
        except Error as e:
            print(f"The error '{e}' occurred")
            return None

    def create_topic(self, topic_name, base_prompt, topic_parent_id=None):
        sql = """
        INSERT INTO topic (topic_name, base_prompt, parent_topic_id, `order`, timestamp) 
        VALUES (%s, %s, %s, %s, NOW())
        """
        try:
            # Execute the query with parameterized values
            self.cursor.execute(sql, (topic_name, base_prompt, topic_parent_id, 1))
            self.connection.commit()

            # Get the ID of the newly inserted topic
            topic_id = self.cursor.lastrowid
            print("Query executed successfully")

            return topic_id
        except Error as e:
            print(f"The error '{e}' occurred")
            return None

    def add_topic_prompt(self, topic_id, role, content):
        sql = """
            INSERT INTO topic_prompts (topic_id, role, content, timestamp) 
            VALUES (%s, %s, %s, NOW())
        """
        try:
            # Execute the query with parameterized values
            self.cursor.execute(sql, (topic_id, role, content))
            self.connection.commit()
            print("Query executed successfully")
        except Error as e:
            print(f"The error '{e}' occurred")

    def get_topic_prompts(self, topic_id):
        # SQL query to get the prompts related to a specific topic_id
        sql = f"SELECT role, content FROM topic_prompts WHERE topic_id = {topic_id} ORDER BY timestamp "
        try:
            self.cursor.execute(sql)
            results = self.cursor.fetchall()

            # Format the results into the required structure
            formatted_result = [{"role": row[0], "content": row[1]} for row in results]

            return formatted_result
        except Error as e:
            print(f"The error '{e}' occurred")
            return None

    def get_chat_response(self, topic_id):
        messages = self.get_topic_prompts(topic_id)
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        chat_response = response.choices[0].message.content
        self.add_topic_prompt(topic_id=topic_id, role="assistant", content=chat_response)
        return chat_response

    def new_topic(self, topic_name, base_prompt, user_input, topic_parent_id=None):
        chat_response = None
        topic_id = self.check_topic_exists(topic_name)
        if topic_id == None:
            topic_id = db.create_topic(topic_name, base_prompt, topic_parent_id)
            base_prompt = self.read_base_prompt(base_prompt)
            self.add_topic_prompt(topic_id,'system', base_prompt)
            self.add_topic_prompt(topic_id,'user', user_input)
            chat_response = self.get_chat_response(topic_id)
            print("New Topic Created")
        else:
            print("Topic Already Exists")
        return self.topic_id, chat_response

    def set_topic_id(self, topic_id):
        self.topic_id = topic_id

    def create_menu(self, json_menu):
        topic_name = "menu"
        base_prompt = "menu_creator"
        db.create_topic(topic_name=topic_name,base_prompt=base_prompt,topic_parent_id=self.topic_id)
        base_prompt = self.read_base_prompt(base_prompt)
        self.add_topic_prompt('system', base_prompt)

    def update_topic_source_files(self, topic_id, chat_response):
        sql = "UPDATE topic SET source_files = %s WHERE topic_id = %s;"
        try:
            # Execute the query with parameterized values
            self.cursor.execute(sql, (chat_response, topic_id))
            self.connection.commit()
            print("Query updated successfully")
        except Error as e:
            print(f"The error '{e}' occurred")
            return None

    def create_the_sub_topics(self, parent_topic_id):
        sql = "SELECT source_files FROM topic WHERE topic_id = %s"
        try:
            self.cursor.execute(sql, (parent_topic_id,))
            result = self.cursor.fetchone()
            sub_topics = json.loads(result[0].replace("```json\n", "").replace("```", ""))
            for sub_topic in sub_topics['system_components']:
                function = sub_topic['function']
                for sub_function in sub_topic['sub_function']:
                    topic_name = sub_function['title']
                    user_input = f"{function} {topic_name} {sub_function['details']}"
                    topic_id, chat_response = db.new_topic(topic_name=topic_name, base_prompt="analyst_programmer",
                                                           user_input=user_input,
                                                           topic_parent_id=parent_topic_id)
            pass
            return None  # Topic does not exist
        except Error as e:
            print(f"The error '{e}' occurred")
            return None
        pass

    def get_sub_topics(self, parent_topic_id):
        sql = "SELECT * FROM topic WHERE parent_topic_id = %s"
        try:
            self.cursor.execute(sql, (parent_topic_id,))
            results = self.cursor.fetchall()

            if results:
                # Fetch the column names
                column_names = [desc[0] for desc in self.cursor.description]
                # Create a list of dictionaries where each dictionary represents a row
                result_list = [dict(zip(column_names, row)) for row in results]
                return result_list
            else:
                return []
        except Error as e:
            print(f"The error '{e}' occurred")
            return []

    def generate_code(self, topic_id):
        script_dir = os.path.dirname(__file__)

        sub_topics = self.get_sub_topics(topic_id)
        for sub_topic in sub_topics:
            file_name = sub_topic['topic_name'].lower().replace(" ","_").replace("-","_")
            file_name = f"{file_name}.html"
            file_path = os.path.join(script_dir, 'html', file_name)
            if sub_topic['source_files'] == None:
                content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Coming Soon</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f3f3f3;
        }
        h1 {
            font-size: 3rem;
            color: #333;
        }
    </style>
</head>
<body>
    <h1>Coming Soon</h1>
</body>
</html>"""
                content = content.replace("Coming Soon",f"{sub_topic['topic_name']}\nComing Soon")
            else:
                content = sub_topic['source_files'].replace('```html\n','').replace('```','')

            try:
                with open(file_path, 'w') as file:
                    file.write(content)
                print(f"Data successfully written to {file_path}")
            except Exception as e:
                print(f"An error occurred: {e}")

        pass

db = DBActions()
action = "generte_html"
if "generate_code" == action:
    db.generate_code(1)
elif "create_sub_topics" == action:
    db.create_the_sub_topics(1)
elif "new_main_topic" == action:
    main_topic_id , chat_response = db.new_topic(topic_name='Islamic Marriage',base_prompt="best_practice_recommenation", user_input='Islamic Marriage')
    list_of_prompts = db.get_topic_prompts(main_topic_id)
    for prompt in list_of_prompts:
        print(prompt['role'],prompt['content'])
    while True:
        user_prompt = input("user_prompt")
        db.add_topic_prompt(main_topic_id, 'user',user_prompt)
        chat_response = db.get_chat_response(main_topic_id)
        if user_prompt.replace(" ", "").upper() == "YES":
            db.update_topic_source_files(main_topic_id, chat_response)
            topic_id , chat_response = db.new_topic(topic_name='Islamic Marriage Menu', base_prompt="menu_creator", user_input=chat_response,
                         topic_parent_id=main_topic_id)
            db.update_topic_source_files(topic_id, chat_response)
            pass
        print(chat_response)
elif "generte_html" == action:
    current_topic_id=17
    list_of_prompts = db.get_topic_prompts(current_topic_id)
    for prompt in list_of_prompts:
        print(prompt['role'], prompt['content'])
    while True:
        user_prompt = input("user_prompt")
        db.add_topic_prompt(topic_id=current_topic_id, role='user', content=user_prompt)
        chat_response = db.get_chat_response(current_topic_id)
        if user_prompt.replace(" ", "").upper() == "YES":
            db.update_topic_source_files(current_topic_id, chat_response)

            pass
        print(chat_response)

