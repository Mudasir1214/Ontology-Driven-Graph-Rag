# MiMEP-Ontology-based-LLM
## Graph RAG Intelligent Q&A System

A powerful **Graph-based Retrieval-Augmented Generation (Graph RAG)** system that combines **Large Language Models (DeepSeek / OpenAI)** with a **Neo4j Knowledge Graph** to deliver **accurate, explainable, and visual question answering**.

---

## 🌟 Key Features

- 🧠 **LLM Integration** — Supports DeepSeek & OpenAI APIs  
- 🕸️ **Graph-Based Reasoning** — Uses Neo4j for structured knowledge retrieval  
- 🎯 **Reduced Hallucination** — Answers strictly grounded in graph data  
- 📊 **Interactive Visualization** — Explore knowledge via graph topology  
- 💬 **Multi-Mode Q&A System**
  - Baseline LLM  
  - Text-based RAG  
  - Graph RAG (Recommended ⭐)  
- 📈 **Automated Benchmarking & Evaluation**

---

## 🏗️ System Architecture

```text
User Query
↓
Graph Retrieval (Neo4j)
↓
Context Construction
↓
LLM (DeepSeek / OpenAI)
↓
Grounded Answer + Graph Reasoning
```
---

## ⚙️ Installation & Setup Guide

Follow these **5 simple phases** to get everything running:

---

## 🛠️ Phase 1: Environment Setup

#### 1️⃣ Create Conda Environment
```bash
conda create -n muda_env
conda activate muda_env
```
#### 2️⃣ Clone Repository
```bash
git clone https://github.com/MuhammadShifa/muda-xin-llm.git
cd muda-xin-llm
```
#### 3️⃣ Install Dependencies
```bash
pip install streamlit streamlit_agraph openai neo4j pandas openpyxl tqdm
```
---

## 🗄️ Phase 2: Neo4j Database Setup

#### 📥 Install Neo4j
- Download Neo4j Community Edition (5.x), unzip it and placed it in `C` drive.
- Ensure Java 17 is installed  
- managed the path in `System Environment Variable`

#### ▶️ Start Neo4j Server
```bash
Open the command prompt and start the neo4j server
neo4j console
```
⚠️ Keep this terminal running at all times

#### 🔐 Set Database Credentials

- Open in browser:  
  [http://localhost:7474](http://localhost:7474)

- 👤 Default Login
  - Username: `neo4j`
  - Password: `neo4j`

- 🔄 Change Password To:
    ```bash
    12345678
    ```
#### ⚠️ Important Note

This password is managed in **.env**.  
If you change it to anything, you must update it in  `.env` where Neo4j authentication is defined.

---

## 🔑 Phase 3: API Key Setup

- **Get API Key**
  - Create an API key from **DeepSeek** or **OpenAI**

- **Add API Key**
  - Open and edit `.env`:

```python
DEEPSEEK_API_KEY = "sk-YOUR_API_KEY"
```
#### ⚠️ Important:
Never expose your API key publicly or push it to GitHub.

---

## 📥 Phase 4: Import Knowledge Graph

Before running the system, you must load data into Neo4j.

#### 📂 Dataset Location

```text
batch_data/
 ├── *.json
 ```

 ▶️ Run Import Script:
```python
python import_json.py
```

✔ This script will:

- Clean existing Neo4j database  
- Parse JSON files  
- Build nodes and relationships  
- Initialize knowledge graph

---

## 🚀 Phase 5: Launch Application

- **Start Streamlit App**:
  ```python
  streamlit run streamlit_app.py
  ```
- **Access the Web App**:
    - Your default web browser should automatically open the app. If it doesn't, manually go to: http://localhost:8501

- **How to Use It**:
  -  Left Sidebar: You can toggle between 3 experimental modes (Baseline LLM, Text RAG, and Graph RAG).
  -  Highly Recommended: Mode 3 (Graph RAG):
     - Click the Live Topology tab to interact with a visual, zoomable spiderweb of your knowledge graph!
     - Click the Intelligent Chat tab to ask engineering questions (e.g., "Is 50mm clearance for Pump Base?").

---


## 📈 Phase 6: Running Automated Benchmark & Auto-Grader

Run large-scale batch testing (e.g., hundreds of questions) and generate a **fully evaluated Excel report**.

#### ✅ Prerequisite
Make sure all previous setup phases are completed successfully.

#### ▶️ Step 1: Run Benchmark Script

```python
python 5a. final_run.py
```
✔ This will:

- Send all questions from `QUESTIONS_DATA` to the LLM  
- Generate responses  
- Save raw outputs in the `output_data/` folder as an Excel File

#### ▶️ Step 2: Extract Correct Answers

```python
python 6a. extract_and_filter_correct_only.py
```
✔ This will:

- Filter and extract only correct answers of Graph RAG
- Save a new Excel file with Correct Only in the `output_data/` folder

#### ▶️ Step 3: Update Final Analysis

```python
python 6b. update_final_analysis_with_correct_only.py"
```
✔ This will:

- Process only correct answers files of Graph Rag
- Generate a refined final analysis benchmark Excel file

#### ▶️ Step 4: Run Auto-Grader

```
python 7. evaluate_and_grade_the_results.py
```
✔ This will:

- Automatically grade all answers
- Highlight results:
  - 🟢 Correct
  - 🔴 Incorrect
- Generate a final polished evaluation report

#### 📂 Output

All generated files will be saved inside:
```
output_data/
```
---

## 🎯 Summary

This pipeline enables:

- Automated evaluation of LLM performance
- Clean filtering of correct responses
- Final graded reports for analysis
- Easy benchmarking across different RAG modes
