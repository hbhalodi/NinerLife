# NinerLife 🎓

**A student workload analysis and planning application designed to help college students understand their workload, track deadlines, and prioritize what needs attention.**

---

## 📌 Overview

College students often manage courses, assignments, exams, work schedules, and other responsibilities across multiple platforms. This can make it difficult to understand how much work is actually coming up and which tasks should be prioritized.

**NinerLife** is being developed to solve this problem by bringing student workload information into one application.

The application analyzes a student's academic workload, tracks assignments and deadlines, and uses that information to help identify urgent and high-priority tasks.

The long-term goal is to develop NinerLife into an **intelligent student planning assistant** that can analyze a student's workload and provide personalized planning recommendations.

---

## 🎯 Problem

Students don't always have a clear picture of their total workload.

For example, a student might have:

* Multiple assignments due during the same week
* Several exams approaching
* A part-time job
* Different levels of difficulty across courses
* Limited study time

Individually, each responsibility may seem manageable. However, when combined, the workload can become overwhelming.

NinerLife aims to make this workload **visible, measurable, and easier to manage.**

---

## ✨ Current Features

### Student Workload Analysis

NinerLife collects basic information about a student's responsibilities, including:

* Number of classes
* Number of assignments
* Number of exams
* Weekly work hours

The application uses this information to calculate a workload score.

### Assignment Management

Students can store multiple assignments with information such as:

* Assignment name
* Course
* Due date
* Difficulty

### Deadline Tracking

NinerLife calculates how many days remain until an assignment is due.

Assignments can be classified as:

* **Overdue**
* **Due Today**
* **Due Soon**
* **Upcoming**

### Assignment Priority

The application considers both:

* How soon the assignment is due
* How difficult the assignment is

It then assigns a priority level such as:

* **Critical**
* **High**
* **Medium**
* **Low**

This helps students identify which assignments deserve attention first.

---

## 🛠️ Technologies

### Current

* **Python**
* Python `datetime`
* Python functions
* Lists
* Dictionaries
* Loops
* Conditional logic

### Planned

As development continues, NinerLife is planned to incorporate:

* **Pandas** — data analysis
* **SQL** — persistent student and assignment data
* **Matplotlib** — workload visualizations
* **AI/LLM technologies** — intelligent planning and recommendations

---

## ⚙️ How It Works

The current version follows a simple workflow:

```text
Student Information
        ↓
Workload Calculation
        ↓
Assignment Information
        ↓
Deadline Analysis
        ↓
Priority Calculation
        ↓
Workload & Assignment Results
```

The goal is to gradually expand this workflow into a more complete student planning system.

---

## 💻 Example

A student might provide information such as:

```text
Classes: 5
Weekly Work Hours: 15
Assignments: 4
Exams: 2
```

NinerLife analyzes these responsibilities and produces a workload assessment.

The student can then provide assignment details:

```text
Assignment: Database Project
Course: ITSC 3162
Due Date: September 10
Difficulty: High
```

NinerLife determines:

```text
Days Remaining: 3
Deadline Status: Due Soon
Priority: High
```

This allows the student to quickly understand what requires attention.

---

## 📂 Project Structure

The project is currently being developed incrementally as new functionality is added.

```text
NinerLife/
│
├── main.py
└── README.md
```

The project structure will evolve as additional components such as data processing, databases, visualization, and AI are introduced.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
```

### 2. Navigate to the project

```bash
cd NinerLife
```

### 3. Run the application

```bash
python main.py
```

The current version runs through the Python terminal and guides the user through the required information.

---

## 🗺️ Development Roadmap

NinerLife is being developed in stages.

### Phase 1 — Python Foundation

* Student workload calculation
* Functions
* Assignment management
* Deadline tracking
* Priority calculation

### Phase 2 — Data Management

* CSV data storage
* Pandas
* Data cleaning and analysis

### Phase 3 — Database

* SQL database
* Store student information
* Store assignments and deadlines
* Connect Python to SQL

### Phase 4 — Visualization

* Workload charts
* Assignment analysis
* Deadline trends
* Workload patterns

### Phase 5 — AI Integration

* Natural-language student input
* Intelligent workload analysis
* Personalized study recommendations
* AI-assisted scheduling
* Student planning assistant

---

## 🔮 Future Vision

The long-term goal of NinerLife is to move beyond simply **tracking** student responsibilities.

Instead, NinerLife should be able to understand a student's situation and help them decide **what to do next**.

For example, a future version could understand:

> "I have a database assignment due Thursday, an exam Friday, and I work 15 hours this week."

The system could analyze the student's workload and generate a realistic plan for completing the most important tasks.

This would transform NinerLife from a workload tracker into an **AI-powered student planning assistant.**

---

## 📚 What This Project Demonstrates

NinerLife is being developed as a practical application of:

* Python programming
* Data structures
* Data analysis
* SQL databases
* Data visualization
* Software development
* AI/LLM integration

The project is designed to demonstrate how these technologies can be combined to solve a real-world problem faced by college students.

---

## 👩‍💻 Author

**Hasti Bhalodia**

Computer Science — Data Science Concentration
UNC Charlotte

---

## 📄 License

This project is currently intended as a personal portfolio and learning project.
