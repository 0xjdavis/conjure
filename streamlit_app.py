import streamlit as st
import os

# PDF Export
from fpdf import FPDF
from datetime import datetime

# COMPONENT - VIEWING HTML FOR WORKFLOW MONITOR
import streamlit.components.v1 as components

# HELPERS
import uuid
from pathlib import Path

# STORAGE
from pinecone import Pinecone
import llama_index
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core import SimpleDirectoryReader,StorageContext, Document, VectorStoreIndex, set_global_handler

# RAG
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore





# LLM
from llama_index.llms.anthropic import Anthropic
from anthropic import Anthropic as AnthropicClient, HUMAN_PROMPT, AI_PROMPT
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

# WORKFLOW
from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Event,
)

# WORKFLOW OBSERVABILITY
from llama_index.utils.workflow import draw_all_possible_flows

# OBSERVABILILITY & EVALUATION USING LLAMATRACE WITH ARIZE PHOENIX
PHOENIX_API_KEY = st.secrets["PHOENIX_API_KEY"]
OTEL_EXPORTER_OTLP_HEADERS = st.secrets["OTEL_EXPORTER_OTLP_HEADERS"]
PHOENIX_CLIENT_HEADERS = st.secrets["PHOENIX_CLIENT_HEADERS"]
PHOENIX_COLLECTOR_ENDPOINT = st.secrets["PHOENIX_COLLECTOR_ENDPOINT"]
llama_index.core.set_global_handler(
    "arize_phoenix", project_name="llamaindex-workflow-pinecone-observability", endpoint="https://llamatrace.com/v1/traces"
)

# DEFINE EVENTS FOR WORKFLOW
class Brainstorming(Event):
    first_output: str

class Brief(Event):
    second_output: str

class Flowchart(Event):
    third_output: str

class Research(Event):
    fourth_output: str

class Journey(Event):
    fifth_output: str


# CUSTOM WORKFLOW
class ProductionWorkflow(Workflow):
    @step
    async def step_one(query, ev: StartEvent) -> Brainstorming:
        #st.write(ev.first_input)
        # Create a temporary document from the query
        temp_doc = Document(text=query)
        temp_index = VectorStoreIndex.from_documents([temp_doc], storage_context=storage_context)
        
        # Perform a similarity search
        retriever = temp_index.as_retriever(similarity_top_k=3)
        similar_docs = retriever.retrieve(query)
        
        if similar_docs:
            return "\n\n".join([f"Similar Project: {doc.text}" for doc in similar_docs])
        else:
            return "No similar projects found."
        
    @step
    async def step_two(self, ev: Brainstorming) -> Brief:
        st.write(ev.first_output)
        return Brief(second_output="Second step complete.")

    @step
    async def step_three(self, ev: Brief) -> Flowchart:
        st.write(ev.second_output)
        return Flowchart(third_output="Third step complete.")
    
    @step
    async def step_four(self, ev: Flowchart) -> Research:
        st.write(ev.third_output)
        return Research(fourth_output="Fourth step complete.")
 
    @step
    async def step_five(self, ev: Research) -> StopEvent:
        st.write(ev.fourth_output)
        return StopEvent(fifth_output="Fourth step complete.")

# EXPORT WORKFLOW TO GRAPH
async def workflow():
    w = ProductionWorkflow(timeout=10, verbose=True)
    result = await w.run(first_input="Start the workflow.")
    st.sidebar.write(result)

if __name__ == "__workflow__":
    import asyncio
    asyncio.run(workflow())

# Load and display the HTML file
URL = "workflow.html"
with st.sidebar:
    with st.expander("Workflow Graph"):
        with open(Path(URL), 'r') as f:
            html_content = f.read()
            draw_all_possible_flows(ProductionWorkflow, filename=URL)
            components.html(html_content, height=500, scrolling=True)

# ==========
# EMBEDDINGS
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

# Initialize Pinecone vector databasee with API Key and OpenAI embed model
PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]

embed_model = OpenAIEmbedding(
    model="text-embedding-3-large",
    dimensions=1536,
)

index_name = "llamaindex-docs"
if not PINECONE_API_KEY:
    st.error("Pinecone API key is not set. Please check your secrets file.")
    st.stop()



def save_content_as_pdf(content, filename, directory="data"):
    """
    Save content to a PDF file in the specified directory.
    """
    try:
        # Create PDF object
        pdf = FPDF()
        pdf.add_page()
        
        # Set font
        pdf.set_font("Arial", size=12)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 10, f"Generated: {timestamp}", ln=True)
        pdf.ln(10)
        
        # Add content
        # Split content into lines and write them to PDF
        lines = content.split('\n')
        for line in lines:
            # Encode string to handle special characters
            encoded_line = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, encoded_line)
        
        # Ensure directory exists
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Save PDF
        filepath = os.path.join(directory, f"{filename}.pdf")
        pdf.output(filepath)
        return True
    except Exception as e:
        st.error(f"Error saving PDF: {str(e)}")
        return False





# ============
# Streamlit UI
st.title("Conjure App Studio")
st.caption("Created by j,davis@sorcery.ai")
st.write("Agentic RAG with a LlamaIndex Workflow, Pinecone and Arize Phoenix for obervability and evaluation. OpenAI Embeddings as well as Anthopic's Claude and Mermaid are used to support workflow output.")

# Initialize components
@st.cache_resource
def init_components():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(index_name)
    
    # Initialize Anthropic LLM for text generation
    llm = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Setup the vector store and storage context
    vector_store = PineconeVectorStore(pinecone_index=index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Initialize Anthropic client
    anthropic_client = AnthropicClient(api_key=ANTHROPIC_API_KEY)
    
    # Return for the initialization function
    return pc, index, llm, vector_store, storage_context, anthropic_client

# Call the initialization function
pc, index, llm, vector_store, storage_context, anthropic_client = init_components()

# Setup tabs for visual display of our workflow output
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Description", "Similar Projects", "Design Brief", "Flowchart", "User Research", "Journey Map", "Prototype"])

# Streamlit UI for user input
tab1.subheader("Enter your project idea")
query = tab1.text_area("Example: A streamlit app for tracking cryptocurrency prices", height=100)

# Custom Mermaid rendering function
with tab4:
    def render_mermaid(code: str) -> None:
        components.html(
            f"""
            <pre class="mermaid">
                {code}
            </pre>
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true }});
            </script>
            """,
            height=500,
        )

# Initialize the RAG system
def initialize_rag():
    # Create data directory if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")
        
    # Load documents from the data directory
    documents = SimpleDirectoryReader(
        input_dir="./data",
        recursive=True,
        exclude_hidden=True
    ).load_data()
    
    # Create parser and parse documents into nodes
    parser = SimpleNodeParser.from_defaults()
    nodes = parser.get_nodes_from_documents(documents)
    
    # Create docstore
    docstore = SimpleDocumentStore()
    docstore.add_documents(documents)
    
    # Create index store
    index_store = SimpleIndexStore()
    
    # Create storage context
    storage_context = StorageContext.from_defaults(
        docstore=docstore,
        index_store=index_store,
        vector_store=vector_store
    )
    
    # Create vector index
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model
    )
    
    return index

# Code generation
def generate_code_step(project_brief, research, flowchart):
    if not all([project_brief, research, flowchart]):
        return None
        
    # Initialize RAG
    index = initialize_rag()
    
    # Create a query engine
    query_engine = index.as_query_engine(
        similarity_top_k=3,
        streaming=True
    )
    
    # Technical-focused prompt
    code_prompt = f"""{HUMAN_PROMPT}Create a basic Streamlit application example with the following technical specifications:

Technical Requirements:
{project_brief}

Components needed:
1. Data handling and processing
2. User interface with Streamlit
3. Basic error handling
4. Data visualization if applicable
5. Configuration management

Please provide the exact code for a minimal viable product with these three components:

1. A requirements.txt file listing only the essential Python packages
2. A setup.py file for installation
3. A main.py file containing a working Streamlit application

Format the output exactly like this:

#### Setup Instructions
Step-by-step technical setup instructions.

#### Requirements
```requirements.txt
streamlit==x.x.x
pandas==x.x.x
... other required packages
```

#### Implementation
```python
# main.py implementation
import streamlit as st
... rest of the code
```

Focus only on the technical implementation. No additional commentary needed.{AI_PROMPT}"""

    with tab7:
        try:
            with st.spinner('Generating prototype...'):
                # Generate code using the correct Anthropic API format
                response = anthropic_client.completions.create(
                    model="claude-2",
                    prompt=code_prompt,
                    max_tokens_to_sample=3000,
                    temperature=0.5
                )
                
                if not response or not response.completion:
                    st.error("No response generated from the AI model")
                    return None
                    
                # Return the completion without displaying anything in this function
                return response.completion
                
        except Exception as e:
            st.error(f"Code generation error: {str(e)}")
            st.exception(e)
            return None

def generate_project_folder_name(query: str, timestamp: str) -> str:
    """
    Generate a folder name from timestamp and query.
    Example: "20240428_143022_crypto_tracking_dashboard"
    """
    # Get first three words from query
    words = query.strip().split()[:3]
    # Clean words (remove special characters, lowercase)
    clean_words = [''.join(c.lower() for c in word if c.isalnum()) for word in words]
    project_name = '_'.join(clean_words)
    return f"{timestamp}-{project_name}"

def save_content_as_pdf(content, filename, project_folder, base_directory="data"):
    """
    Save content to a PDF file in a project-specific directory.
    """
    try:
        # Create PDF object
        pdf = FPDF()
        pdf.add_page()
        
        # Set font
        pdf.set_font("Arial", size=12)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 10, f"Generated: {timestamp}", ln=True)
        pdf.ln(10)
        
        # Add content
        # Split content into lines and write them to PDF
        lines = content.split('\n')
        for line in lines:
            # Encode string to handle special characters
            encoded_line = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, encoded_line)
        
        # Create project directory path
        project_dir = os.path.join(base_directory, project_folder)
        
        # Ensure directory exists
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
        
        # Save PDF
        filepath = os.path.join(project_dir, f"{filename}.pdf")
        pdf.output(filepath)
        
        # Return the filepath for reference
        return filepath
    except Exception as e:
        st.error(f"Error saving PDF: {str(e)}")
        return None



# Define the workflow function
def main_workflow(query):
    if not query:
        st.error("Please enter a project idea first.")
        return False

    # Create a timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate project folder name
    project_folder = generate_project_folder_name(query, timestamp)
    
    # Create sidebar status container
    status_container = st.sidebar.container()
    
    # Step 1: Similar Projects
    similar_projects = find_similar_projects(query)
    if similar_projects:
        tab2.subheader("Similarity Search Results")
        tab2.write(similar_projects)
        # Save to PDF
        filepath = save_content_as_pdf(similar_projects, "01_similar_projects", project_folder)
        if filepath:
            status_container.success(f"✓ Similarity Search completed!")
    else:
        tab2.error("Failed to find similar projects")
        return False

    # Step 2: Project Brief
    project_brief = brainstorm_step(query)
    if project_brief:
        tab3.subheader("Project Design Brief")
        tab3.write(project_brief)
        # Save to PDF
        filepath = save_content_as_pdf(project_brief, "02_project_brief", project_folder)
        if filepath:
            status_container.success(f"✓ Project Brief completed!")
    else:
        tab3.error("Failed to generate project brief")
        return False

    # Step 3: Flowchart
    flowchart = flowchart_step(project_brief)
    if flowchart:
        tab4.subheader("Flowchart and Recommendations")
        with tab4:
            st.write(flowchart)
            mermaid_start = flowchart.find("```mermaid")
            if mermaid_start != -1:
                mermaid_end = flowchart.find("```", mermaid_start + 10)
                if mermaid_end != -1:
                    mermaid_code = flowchart[mermaid_start+10:mermaid_end].strip()    
                    render_mermaid(mermaid_code)
        # Save to PDF
        filepath = save_content_as_pdf(flowchart, "03_flowchart", project_folder)
        if filepath:
            status_container.success(f"✓ Flowchart completed!")
    else:
        tab4.error("Failed to generate flowchart")
        return False

    # Step 4: Research
    research = research_step(project_brief)
    if research:
        tab5.subheader("Persona, Scenario, and User Interview Questions")
        tab5.write(research)
        # Save to PDF
        filepath = save_content_as_pdf(research, "04_research", project_folder)
        if filepath:
            status_container.success(f"✓ User Research completed!")
    else:
        tab5.error("Failed to generate research")
        return False

    # Step 5: Journey
    journey = journey_step(project_brief)
    if journey:
        tab6.subheader("User Journey")
        with tab6:
            st.write(journey)
            mermaid_start = journey.find("```mermaid")
            if mermaid_start != -1:
                mermaid_end = journey.find("```", mermaid_start + 10)
                if mermaid_end != -1:
                    mermaid_code = journey[mermaid_start+10:mermaid_end].strip()    
                    render_mermaid(mermaid_code)
        # Save to PDF
        filepath = save_content_as_pdf(journey, "05_journey", project_folder)
        if filepath:
            status_container.success(f"✓ Journey Map completed!")
    else:
        tab6.error("Failed to generate journey map")
        return False

    # Step 6: Code Generation
    # Important fix: passing the correct parameters
    code = generate_code_step(project_brief, research, flowchart)
    if code:
        tab7.subheader("Generated Prototype")
        tab7.write(code)  # Display the generated code in the tab
        # Save to PDF
        filepath = save_content_as_pdf(code, "06_prototype", project_folder)
        if filepath:
            status_container.success(f"✓ Prototype completed!")
    else:
        tab7.error("Failed to generate prototype code")
        return False

    status_container.success("✨ All documents have been saved successfully!")
    return True

# WORKFLOW STEP FUNCTIONS
# Function to find similar projects
# START WORKFLOW | TAB 2 - SIMILAR PROJECTS
def find_similar_projects(query):
    # Create a temporary document from the query
    temp_doc = Document(text=query)
    temp_index = VectorStoreIndex.from_documents([temp_doc], storage_context=storage_context)
    
    # Perform a similarity search
    retriever = temp_index.as_retriever(similarity_top_k=3)
    similar_docs = retriever.retrieve(query)
    
    if similar_docs:
        tab2.write("Your idea might not be as original as you thought...")
        return "\n\n".join([f"- {doc.text}" for doc in similar_docs])
    else:
        tab2.write("Wow! Your idea seems like it might be quite original...")
        return "No similar projects found."


# STEP 2 | TAB 3 - BRAINSTORM FOR DESIGN BRIEF
def brainstorm_step(query):
    brainstorm_prompt = f"{HUMAN_PROMPT} Use '{query}' as the problem and define the solution by outlining experience highlighting pain points and explaining how your solutions resolve an issue, conflict or problem. Create and output a Project Design Brief with the following sections:\n\n1. Target Market\n2. Target Audience\n3. Competitors\n4. Project Description\n5. Technical Requirements\n6. Expected Outcome from using the product\n7. Estimated number of potential users\n8. Estimated number of potential business partners\n9. Expected revenue for first year in operation\n10. Explanation of monetization strategy\n\nPlease format your response as a structured document with clear headings for each section.{AI_PROMPT}"

    with tab3:
        try:
            # Generate a response using Anthropic LLM
            response = anthropic_client.completions.create(
                model="claude-2",
                prompt=brainstorm_prompt,
                max_tokens_to_sample=1000
            )
            project_design_brief = response.completion
            
            # Store the project brief in Pinecone
            doc_id = str(uuid.uuid4())
            doc = Document(text=project_design_brief, id_=doc_id)
            VectorStoreIndex.from_documents([doc], storage_context=storage_context)
            return project_design_brief
        except Exception as e:
            st.error(f"An error occurred while generating the project brief: {str(e)}")
            return None

# STEP 3 | TAB 4 - FLOWCHART
def flowchart_step(project_design_brief):
    flowchart_prompt = f"{HUMAN_PROMPT} Based on the following Project Design Brief, please:\n\n1. Create a Mermaid flowchart describing the basic architecture of the project.\n2. Provide recommendations or suggestions on other features or considerations that might be useful.\n\nProject Design Brief:\n{project_design_brief}\n\nPlease format your response in two sections:\n1. Mermaid Flowchart\n2. Recommendations and Suggestions\n\nFor the Mermaid flowchart, use the following syntax:\n```mermaid\ngraph TD\n    A[Start] --> B[Process]\n    B --> C[End]\n```\n\nReplace the example with an appropriate flowchart for the project.{AI_PROMPT}"

    with tab4:
        try:
            # Generate flowchart response
            response = anthropic_client.completions.create(
                model="claude-2",
                prompt=flowchart_prompt,
                max_tokens_to_sample=1000
            )
            return response.completion
        except Exception as e:
            st.error(f"An error occurred while generating the flowchart: {str(e)}")
            return None

# STEP 4  | TAB 5 - USER RESEARCH
def research_step(project_design_brief):
    if not project_design_brief:
        return None
        
    research_prompt = f"{HUMAN_PROMPT} Based on the following Project Design Brief, please:\n\n1. Create a Persona\n\n2. Create a day in the life scenario for the Persona to describe the problem the application will solve highlighting the pain points of the experience.\n\n3. Create a list of 10 questions for a user interview for the persona. Ask these questions to strategically balance both quantitative and qualitative aspects of user research principles.\n\nProject Design Brief:\n{project_design_brief}\n\nPlease format your response in three sections:\n1. Persona\n2. Scenario\n3. Interview\n\n{AI_PROMPT}"

    with tab5:
        try:
            with st.spinner('Generating research deliverables...'):
                response = anthropic_client.completions.create(
                    model="claude-2",
                    prompt=research_prompt,
                    max_tokens_to_sample=1000
                )
                if not response or not response.completion:
                    st.error("No response generated from the AI model")
                    return None
                return response.completion
        except Exception as e:
            st.error(f"Research step error: {str(e)}")
            st.exception(e)  # This will show the full traceback
            return None

# STEP 5  | TAB 6 - USER JOURNEY
def journey_step(project_design_brief):
    if not project_design_brief:
        return None
        
    journey_prompt = f"{HUMAN_PROMPT} Based on the following Project Design Brief, create a user journey map using Mermaid diagram syntax. Include the following stages: Awareness, Consideration, Decision, Onboarding, and Retention. For each stage, show the user's actions, thoughts, and emotions.\n\nProject Design Brief:\n{project_design_brief}\n\nPlease format your response using Mermaid graph syntax within ```mermaid``` tags.{AI_PROMPT}"

    with tab6:
        try:
            with st.spinner('Generating journey map...'):
                response = anthropic_client.completions.create(
                    model="claude-2",
                    prompt=journey_prompt,
                    max_tokens_to_sample=1000
                )
                if not response or not response.completion:
                    st.error("No response generated from the AI model")
                    return None
                return response.completion
        except Exception as e:
            st.error(f"Journey step error: {str(e)}")
            st.exception(e)  # This will show the full traceback
            return None

# RUN WORKFLOW BUTTON
with tab1:
    if st.button("Run Workflow"):
        with st.spinner("Running workflow..."):
            result = main_workflow(query)
        if result:
            st.success("Workflow completed successfully!")
        else:
            st.error("Workflow failed to complete. Please check the error messages.")

