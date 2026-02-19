# AI Natural Language SQL Query System (IntelliSQL)

IntelliSQL is an AI-powered application that allows users to interact with a database using plain English instead of writing SQL queries manually.
The system uses Google Gemini AI to understand user questions, convert them into SQL queries, execute them on a database, and display the results in a web interface.

---

## 🚀 Features

* Convert natural language questions into SQL queries
* Automatic database querying
* Interactive Streamlit web interface
* Supports analytical queries (count, average, highest, filtering)
* Beginner-friendly database interaction

---

## 🧠 How It Works

1. User enters a question in English
2. Gemini AI converts the question into SQL
3. SQL query runs on SQLite database
4. Results are displayed in the browser

**Flow:**
Natural Language → AI Model → SQL Query → Database → Results

---

## 🛠 Tech Stack

* Python
* Google Gemini API (LLM)
* SQLite
* Streamlit
* Prompt Engineering (NL → SQL)

---

## 📂 Project Structure

```
├── app.py            # Main application
├── sql.py            # Database creation script
├── student.db        # SQLite database
├── requirements.txt  # Dependencies
├── .env              # API key (not uploaded)
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/lovaraju4406/AI-Natural-Language-SQL-Query-System-IntelliSQL-.git
cd AI-Natural-Language-SQL-Query-System-IntelliSQL-
```

---

### 2. Create Virtual Environment

```bash
python -m venv myenv
myenv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Add Gemini API Key

Create a `.env` file in the root folder:

```
GOOGLE_API_KEY=your_api_key_here
```

---

### 5. Create Database

```bash
python sql.py
```

---

### 6. Run Application

```bash
streamlit run app.py
```

Open browser:

```
http://localhost:8501
```

---

## 🧪 Example Queries

* show all students
* who got highest marks
* average marks
* students in Data Science class

---

## 🎯 Objective

To simplify database interaction by enabling non-technical users to retrieve information using natural language with the help of AI.

---

## 👨‍💻 Author

Lovaraju Dungala
