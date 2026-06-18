# Ontology-driven Graph RAG for Traceable Compliance Reasoning and Conflict Detection in Modular Hospital Building Services Design
## OD-GRAG Intelligent Q&A System

A powerful **Ontology-driven Graph Retrieval-Augmented Generation (OD-GRAG)** system that combines **Large Language Models (DeepSeek / OpenAI)** with a **Ontology-driven Knowledge Graph** in Neo4j to deliver **accurate, explainable, and visual question answering** without any hallucination.

---

## 🌟 Key Features

- 🧠 **LLM Integration** — Supports DeepSeek & OpenAI APIs  
- 🕸️ **Graph-Based Reasoning** — Uses Neo4j for structured knowledge retrieval  
- 🎯 **Reduced Hallucination** — Answers strictly grounded in graph data  
- 📊 **Interactive Visualization** — Explore knowledge via graph topology  
- 💬 **Multi-Mode Q&A System**
  - STandalone LLMs (No RAG)  
  - Vector-based text RAG
  - Generic graph-based RAG
  - Hybrid RAG  
  - Ontology-driven graph RAG (Recommended ⭐)  
- 📈 **Automated Benchmarking & Evaluation**

---

## 🏗️ System Architecture

```text
User Query
↓
OD-GRAG Retrieval (Neo4j)
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
https://github.com/Mudasir1214/Ontology-Driven-Graph-Rag
```
#### 3️⃣ Install Dependencies
```bash
pip install streamlit streamlit_agraph openai neo4j pandas openpyxl tqdm faiss-cpu
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
input_data/
├── batch_data/
  ├── *.json
├── data_ductile.json
├── text_data.json
 ```

 ▶️ Run Import Script:
```python
python 4a. import_batch_json_to_neo4j.py
```

✔ This script will:

- Clean existing Neo4j database  
- Parse Batch JSON files  
- Build nodes and relationships  
- Initialize knowledge graph

```python
python 4b. import_ductile_json_to_neo4j.py
```

✔ This script will:

- append additional data to Neo4j database  
- Parse Ductile JSON files for Proposed Ontalogy RAG

```python
python 4c. build_faiss_index_for_vector_rag.py
```

✔ This script will:

- index the embedded data of text_data.json into FAISS  
---

## 🚀 Phase 5: Launch Application

- **Start Streamlit App**:
  ```python
  cd app
  streamlit run app.py
  ```
- **Access the Web App**:
    - Your default web browser should automatically open the app. If it doesn't, manually go to: http://localhost:8501

- **How to Use It**:
  -  Left Sidebar: You can toggle between 5 experimental modes (Baseline (Pure LLM), Vector RAG, Graph RAG, Hybrid RAG, Proposed Ontalogy based RAG).
  -  Highly Recommended: Mode 5 (Proposed ontology based RAG):
     - Click the `Chat` tab to ask any question regarding the modular hospital building services design
     - Click the `Retrieved Knowledge` tab to check the sources of retrieved knowledge for each relevant questions asked.

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
