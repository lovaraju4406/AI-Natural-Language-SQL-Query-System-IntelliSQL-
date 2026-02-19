import sqlite3
import random

## Connect To SQLite database
connection = sqlite3.connect("student.db")
cursor = connection.cursor()

## Drop existing table to avoid duplicate data if rerun
cursor.execute("DROP TABLE IF EXISTS STUDENT")

## Create the table
table_info = """
CREATE TABLE IF NOT EXISTS STUDENT (
    NAME    VARCHAR(50),
    CLASS   VARCHAR(30),
    SECTION VARCHAR(5),
    GENDER  VARCHAR(10),
    MARKS   INT
);
"""
cursor.execute(table_info)

# ── Name Pools ────────────────────────────────────────────────────────────────

BOYS = [
    "Aarav","Aditya","Akash","Akshay","Amit","Anand","Aniket","Anil","Anish","Ankit",
    "Ankur","Arjun","Arnav","Aryan","Ashish","Ashok","Atharv","Ayaan","Bharat","Chetan",
    "Darshan","Deepak","Dev","Dhruv","Dinesh","Divyansh","Farhan","Gaurav","Girish","Harish",
    "Harsh","Hemant","Hitesh","Ishan","Ishaan","Jatin","Jayesh","Kartik","Kiran","Kishan",
    "Krishna","Kunal","Lokesh","Madhav","Mahesh","Manav","Manish","Manoj","Milan","Mohan",
    "Mohit","Mukesh","Naveen","Nikhil","Nilesh","Nishant","Om","Pankaj","Parth","Piyush",
    "Pranav","Prashant","Praveen","Raj","Rajan","Rajesh","Rahul","Ramesh","Rishabh","Rohan",
    "Rohit","Sachin","Sahil","Sai","Sanjay","Saurabh","Shivam","Shubham","Siddhant","Siddharth",
    "Soham","Sourabh","Sudhanshu","Sumit","Suraj","Tarun","Tejas","Tushar","Uday","Vaibhav",
    "Vijay","Vikas","Vikram","Vikash","Vinay","Vishal","Vivek","Yash","Yogesh","Darius",
    "Krish","Dipesh","Karthik","Ajay","Akhil","Balaji","Chandra","Dheeraj","Gopal","Harshad",
    "Jagdish","Kamlesh","Laxman","Mithun","Naresh","Omkar","Paras","Prakash","Ravi","Sagar",
    "Santosh","Satish","Swapnil","Umesh","Vipul","Aakash","Abhijeet","Abhimanyu","Abhinav","Abhishek",
]

GIRLS = [
    "Aakanksha","Aarti","Aishwarya","Akanksha","Amrita","Ananya","Anjali","Ankita","Anuja","Aparna",
    "Archana","Arushi","Asha","Ashwini","Bhavana","Chetna","Deepa","Deepika","Devika","Diksha",
    "Divya","Diya","Durga","Ekta","Garima","Gayatri","Geeta","Harshita","Heena","Ishita",
    "Jyoti","Kajal","Kalyani","Kamini","Kavita","Kavya","Kirti","Komal","Kriti","Lakshmi",
    "Lavanya","Laxmi","Madhuri","Manasi","Manisha","Meera","Meghna","Megha","Mili","Mira",
    "Monika","Nandini","Neha","Nikita","Nisha","Nitu","Pallavi","Payal","Pooja","Preeti",
    "Priya","Priyanka","Puja","Radha","Ragini","Rashmi","Rekha","Renu","Riya","Ritika",
    "Roshni","Ruhi","Rupali","Sakshi","Sandhya","Sapna","Sarika","Seema","Shefali","Shilpa",
    "Shital","Shivani","Shreya","Shruti","Simran","Sneha","Sonal","Sonali","Sonam","Sonia",
    "Swati","Tanvi","Tanya","Tripti","Usha","Vandana","Varsha","Veena","Vidya","Vipasa",
    "Vrinda","Yamini","Aarohi","Aditi","Aishani","Akriti","Alka","Amisha","Amita","Anita",
    "Bhavya","Chhaya","Deeksha","Drishti","Esha","Falguni","Geetanjali","Hansika","Hema","Indira",
    "Jayshree","Jhanvi","Juhi","Kalpana","Kanchan","Kusum","Lata","Madhu","Mamta","Manju",
]

def pick_name(gender, used):
    pool = BOYS if gender == "Male" else GIRLS
    available = [n for n in pool if n not in used]
    if not available:
        pool_extra = [f"{n}{random.randint(2,9)}" for n in pool]
        available = [n for n in pool_extra if n not in used]
    name = random.choice(available)
    used.add(name)
    return name

def marks_for_section(section):
    """Different sections have slightly different performance profiles."""
    profiles = {
        "A":  (72, 18),   # best section
        "B":  (68, 17),
        "C":  (65, 16),
        "D":  (62, 17),
        "E":  (58, 18),   # weakest section
    }
    mean, std = profiles.get(section, (65, 17))
    m = int(random.gauss(mean, std))
    return max(25, min(100, m))   # clamp between 25 and 100

# ── Department Configuration ─────────────────────────────────────────────────
# Each department has sections, and each section ~30 students (half boys, half girls)

DEPARTMENTS = {
    # dept_name        : [sections]
    "CSE":             ["A", "B", "C"],   # ~90  students (3 sections × 30)
    "Data Science":    ["A", "B"],        # ~60  students (2 sections × 30)
    "AIML":            ["A", "B"],        # ~60  students (2 sections × 30)
    "CSE-AIML":        ["A", "B"],        # ~60  students (2 sections × 30)
    "CAI":             ["A", "B"],        # ~60  students (2 sections × 30)
}

SECTION_SIZE = 30   # ~30 students per section (15 boys + 15 girls)

# ── Insert Records ────────────────────────────────────────────────────────────
used_names = set()
total_inserted = 0

for dept, sections in DEPARTMENTS.items():
    for section in sections:
        boys_count  = SECTION_SIZE // 2
        girls_count = SECTION_SIZE - boys_count

        for _ in range(boys_count):
            name   = pick_name("Male", used_names)
            marks  = marks_for_section(section)
            cursor.execute(
                "INSERT INTO STUDENT VALUES (?, ?, ?, ?, ?)",
                (name, dept, section, "Male", marks)
            )
            total_inserted += 1

        for _ in range(girls_count):
            name   = pick_name("Female", used_names)
            marks  = marks_for_section(section)
            cursor.execute(
                "INSERT INTO STUDENT VALUES (?, ?, ?, ?, ?)",
                (name, dept, section, "Female", marks)
            )
            total_inserted += 1

## ── Display Summary ──────────────────────────────────────────────────────────
print("=" * 70)
print(f"{'IntelliSQL — Student Database':^70}")
print("=" * 70)

data = cursor.execute("SELECT CLASS, SECTION, COUNT(*) as CNT, ROUND(AVG(MARKS),1) as AVG FROM STUDENT GROUP BY CLASS, SECTION ORDER BY CLASS, SECTION").fetchall()
print(f"\n{'Department':<20} {'Section':<10} {'Students':<12} {'Avg Marks'}")
print("-" * 55)
for row in data:
    print(f"{row[0]:<20} {row[1]:<10} {row[2]:<12} {row[3]}")

gender_data = cursor.execute("SELECT GENDER, COUNT(*) FROM STUDENT GROUP BY GENDER").fetchall()
print("\n" + "-" * 55)
for g, cnt in gender_data:
    print(f"  {g}: {cnt} students")

total_check = cursor.execute("SELECT COUNT(*) FROM STUDENT").fetchone()[0]
avg_overall = cursor.execute("SELECT ROUND(AVG(MARKS),1) FROM STUDENT").fetchone()[0]
top_marks   = cursor.execute("SELECT MAX(MARKS) FROM STUDENT").fetchone()[0]
print(f"\n  Total Students : {total_check}")
print(f"  Overall Avg    : {avg_overall}")
print(f"  Top Score      : {top_marks}")
print("=" * 70)

## ── Commit and Close ─────────────────────────────────────────────────────────
connection.commit()
connection.close()

print(f"\n✅ student.db created with {total_check} students!")
print("Departments : CSE (A,B,C) | Data Science (A,B) | AIML (A,B) | CSE-AIML (A,B) | CAI (A,B)")
print("Sections    : A = top performers, B = average, C/D/E = mixed")
print("Gender      : ~50% Boys, ~50% Girls per section")
print("Marks Range : 25 to 100")