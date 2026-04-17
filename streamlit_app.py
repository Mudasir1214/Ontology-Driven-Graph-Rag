import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from neo4j import GraphDatabase
from streamlit_agraph import agraph, Node, Edge, Config
import pandas as pd
import json
import os
import time

# Load environment variables
load_dotenv()

# ==========================================
# 1. Global Configuration and Cache Optimization
# ==========================================
st.set_page_config(
    layout="wide", 
    page_title="RAG Intelligent Workbench", 
    page_icon="🧬", 
    initial_sidebar_state="expanded"
)

# Inject optimized CSS
st.markdown("""
<style>
    /* App base */
    .stApp {
        background-color: #FFFFFF;
        color: #111;
        font-family: 'Segoe UI', serif;
    }

    #MainMenu, footer, header {visibility: hidden;}

    /* Chat container */
    .chat-container {
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        background-color: #FAFAFA;
        padding: 20px;
    }

    /* ✅ FIX: Force chat text color */
    .stChatMessage {
        background-color: #FFFFFF !important;
        color: #111 !important;
    }

    .stChatMessage p {
        color: #111 !important;
    }

    /* Also fix markdown text */
    .stMarkdown {
        color: #111 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {gap: 20px;}
    .stTabs [data-baseweb="tab"] {height: 50px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. Core Connections (Using Cache to Avoid Lag)
# ==========================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

TEXT_DATA_FILE = "./input_data/text_data.json"

# 🟢 Cache 1: Database driver
@st.cache_resource
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

# 🟢 Cache 2: Full graph data
@st.cache_data
def get_visualization_data():
    try:
        driver = get_driver()
        with driver.session() as session:
            # Query nodes
            c_n = "MATCH (n) RETURN n.id AS ID, COALESCE(n.title, n.name, n.id) AS Label, labels(n)[0] AS Type"
            df_n = pd.DataFrame([r.data() for r in session.run(c_n)])
            # Query relationships
            c_r = "MATCH (a)-[r]->(b) RETURN a.id AS Source, type(r) AS Type, b.id AS Target"
            df_r = pd.DataFrame([r.data() for r in session.run(c_r)])
        return df_n, df_r
    except:
        return pd.DataFrame(), pd.DataFrame()

# 🟢 Cache 3: Load text data
@st.cache_data
def load_text_corpus():
    if not os.path.exists(TEXT_DATA_FILE): return []
    with open(TEXT_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('entries', [])

# ==========================================
# 3. Core RAG Logic
# ==========================================

# --- A. Text RAG ---
def retrieve_text_context(query):
    entries = load_text_corpus()
    if not entries: return ""
    
    keywords = query.lower().split()
    hits = []
    
    for entry in entries:
        content = entry.get('text', '').lower()
        score = sum(1 for kw in keywords if kw in content)
        if score > 0:
            hits.append((score, f"[{entry.get('chapter', 'Ref')}] {entry.get('text', '')}"))
    
    hits.sort(key=lambda x: x[0], reverse=True)
    return "\n\n".join([h[1] for h in hits[:3]])

# --- B. Graph RAG (Full context retrieval) ---
def retrieve_graph_context(query):
    driver = get_driver()
    context = ""
    try:
        with driver.session() as session:
            # 1. Keyword extraction
            raw_keywords = query.lower().replace("?", "").replace("chapter", "").split()
            stop_words = ["does", "the", "include", "any", "material", "specifications", "if", "not", "where", "are", "they", "defined", "what", "is", "in", "install", "requirement"]
            valid_keywords = [k for k in raw_keywords if k not in stop_words and len(k) > 2]
            
            if not valid_keywords: valid_keywords = ["pipework"]
            
            search_conditions = " OR ".join([f"toLower(n.name) CONTAINS '{k}' OR toLower(n.title) CONTAINS '{k}'" for k in valid_keywords])
            
            # 2. Broad Cypher query
            cypher = f"""
            MATCH (n)
            WHERE ({search_conditions})
            OPTIONAL MATCH path = (n)-[*1..3]-(target)
            WHERE labels(target)[0] IN ['Rule', 'Component', 'Material']
            WITH path, n
            UNWIND nodes(path) as node
            RETURN DISTINCT 
                labels(node)[0] as Type,
                coalesce(node.name, node.title, node.id) as Name,
                coalesce(node.text, "No Content") as Content
            LIMIT 20
            """
            
            result = session.run(cypher)
            
            # 3. Format results
            lines = []
            for row in result:
                if row['Type'] == 'Rule':
                    lines.append(f"[Rule] {row['Name']}: {row['Content']}")
                elif row['Type'] == 'Material':
                    lines.append(f"[Material Info] {row['Name']}: {row['Content']}")
                elif row['Type'] == 'Chapter':
                    lines.append(f"[Chapter Source] {row['Name']}")
            
            context = "\n\n".join(lines)
            
            if not context:
                context = "No graph path found. (System hint: Try keywords like 'Mechanical' or 'Pipework')"
                
    except Exception as e:
        return f"Graph Query Error: {e}"
        
    return context

# ==========================================
# 4. Sidebar and State
# ==========================================
with st.sidebar:
    st.header("⚙️ Experiment Control")
    mode = st.radio(
        "Select Model Architecture:",
        ("1. Baseline (Pure LLM)", "2. Text-Enhanced (Text RAG)", "3. Graph-Enhanced (Graph RAG)")
    )
    st.divider()
    if st.button("🧹 Clear History"):
        for key in ["history_pure", "history_text", "history_graph"]:
            st.session_state[key] = []
        st.rerun()

# Initialize session
for key in ["history_pure", "history_text", "history_graph", "messages"]:
    if key not in st.session_state: st.session_state[key] = []

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# ==========================================
# 5. Main Logic: Three Modes
# ==========================================

# --- Mode 1: Baseline ---
if mode == "1. Baseline (Pure LLM)":
    st.title("🤖 Mode 1: Baseline (Standard Model)")
    st.info("Uses DeepSeek-V3 internal knowledge only. May produce generalized answers.")
    
    chat_box = st.container(height=650, border=True)
    with chat_box:
        if not st.session_state.history_pure: st.write("System Ready.")
        for msg in st.session_state.history_pure:
            st.chat_message(msg["role"]).write(msg["content"])
            
    if prompt := st.chat_input("Ask a question..."):
        st.session_state.history_pure.append({"role": "user", "content": prompt})
        with chat_box:
            st.chat_message("user").write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    stream = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}], stream=True
                    )
                    res = st.write_stream(stream)
                st.session_state.history_pure.append({"role": "assistant", "content": res})

# --- Mode 2: Text-Enhanced (Text RAG) ---
elif mode == "2. Text-Enhanced (Text RAG)":
    st.title("📄 Mode 2: Text-Enhanced (Keyword Search)")
    
    t_chat, t_db = st.tabs(["💬 Intelligent Chat", "📚 Raw Text Database"])
    
    # Tab 1: Chat
    with t_chat:
        st.caption("Retrieves raw text chunks from text_data.json based on keywords.")
        
        # Show history
        for msg in st.session_state.history_text:
            st.chat_message(msg["role"]).write(msg["content"])
        
        if prompt := st.chat_input("Ask about specs..."):
            st.session_state.history_text.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Searching text documents..."):
                    response_ctx = retrieve_text_context(prompt)
                    
                    st.markdown(f"**Retrieved Context:**\n\n{response_ctx}")
                    
                    # You can add LLM generation here; currently only retrieval is shown
                    final_res = f"Text Found!\n\nContent:\n{response_ctx}"
                    st.session_state.history_text.append({"role": "assistant", "content": final_res})

    # Tab 2: Database
    with t_db:
        st.subheader("📂 All Text Data")
        try:
            with open(TEXT_DATA_FILE, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if "entries" in raw_data:
                df = pd.DataFrame(raw_data["entries"])
                st.info(f"📊 Total Records: {len(df)}")
                st.dataframe(df, use_container_width=True , column_config={"chapter": "Source", "text": "Content"})
        except:
            st.error("Text data not found.")

# --- Mode 3: Graph RAG (The Best One) ---
elif mode == "3. Graph-Enhanced (Graph RAG)":
    st.title("🕸️ Mode 3: Graph-Enhanced (Deep Reasoning)")
    
    t_chat, t_viz, t_data = st.tabs(["💬 Intelligent Chat", "🕸️ Live Topology", "📊 Raw Data"])
    
    # Tab 1: Chat
    with t_chat:
        st.caption("Retrieves structured relationships and rule details from Neo4j.")
        c1, c2 = st.columns([7, 3])
        with c1:
            chat_box = st.container(height=600, border=True)
            with chat_box:
                if not st.session_state.history_graph: st.success("Neo4j Connected.")
                for msg in st.session_state.history_graph: st.chat_message(msg["role"]).write(msg["content"])
        with c2:
            st.subheader("🔍 Graph Context")
            graph_ctx_container = st.empty()
            
        if prompt := st.chat_input("Ask complex engineering questions..."):
            st.session_state.history_graph.append({"role": "user", "content": prompt})
            with chat_box: st.chat_message("user").write(prompt)
            
            # Retrieval
            ctx = retrieve_graph_context(prompt)
            with c2: 
                if ctx: st.info("Graph Paths:"); st.code(ctx, language="text")
                else: st.warning("No path found.")
            
            # Generation
            sys = f"""You are an expert. Answer based on the Graph Context. 
            If context contains rules, quote them with their IDs.
            Context:
            {ctx}"""
            
            with chat_box:
                with st.chat_message("assistant"):
                    with st.spinner("Reasoning on graph..."):
                        stream = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "system", "content": sys}, {"role": "user", "content": prompt}], stream=True
                        )
                        res = st.write_stream(stream)
                    st.session_state.history_graph.append({"role": "assistant", "content": res})

   # Tab 2: Visualization
    with t_viz:
        st.subheader("🕸️ Knowledge Topology")
        df_n, df_r = get_visualization_data() 
        
        if not df_n.empty:
            nodes = []
            seen_ids = set() # ✨ Track drawn node IDs to avoid duplication
            
            colors = {
                "Document": "#D32F2F", "Chapter": "#F57C00", "Rule": "#388E3C",
                "Component": "#1976D2", "Module": "#7B1FA2", "Constraint": "#0097A7",
                "ConstraintGroup": "#00BCD4", "Material": "#795548", "WorkStep": "#C2185B"
            }
            
            # 1. Node deduplication and creation
            for _, r in df_n.iterrows():
                node_id = str(r['ID'])
                
                # ✨ Core filter: skip if already drawn or invalid
                if node_id in seen_ids or node_id == "None":
                    continue
                    
                seen_ids.add(node_id) # record
                
                lbl = str(r['Label'])
                node_type = r['Type']
                short = lbl[:15] + "..." if len(lbl) > 15 else lbl
                
                nodes.append(Node(
                    id=node_id, 
                    label=short, 
                    title=f"[{node_type}] {lbl}", 
                    size=25 if node_type == "Rule" else 18, 
                    color=colors.get(node_type, "#9e9e9e"),
                    font={'color': 'black', 'size': 12, 'face': 'arial'}
                ))
            
            # 2. Edge deduplication and creation
            edges = []
            seen_edges = set()
            for _, r in df_r.iterrows():
                source_id = str(r['Source'])
                target_id = str(r['Target'])
                edge_sig = f"{source_id}-{target_id}" # unique signature
                
                # ✨ Ensure edge is unique and nodes exist
                if edge_sig not in seen_edges and source_id in seen_ids and target_id in seen_ids:
                    seen_edges.add(edge_sig)
                    edges.append(Edge(source=source_id, target=target_id, color="#B0BEC5", type="arrow"))
            
            config = Config(
                width=1200, height=750, directed=True, physics=True, fit=True,
                gravity=-1000, centralGravity=0.6, springLength=70, 
                nodeHighlightBehavior=True, backgroundColor="#FFFFFF"
            )
            
            st.caption("Legend: 🔴Document 🟠Chapter 🟢Rule 🔵Component 🟣Module 🟤Material")
            agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.warning("No data in Neo4j.")

    # Tab 3: Data
    with t_data:
        df_n, df_r = get_visualization_data()
        st.dataframe(df_n, use_container_width=True)