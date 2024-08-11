# ragBot
A customizable framework for creating an Azure search index from PDFs/Docx/Excel files, and using it in a RAG based chatbot.

<img src="https://github.com/kbansal98/ragBot/blob/main/ragArch.jpg"/>

## Requirements

The necessary requirements for running the index creation are shown below. 

```python
!pip install azure-identity==1.15.0
!pip install tiktoken
!pip install fitz
!pip install langchain==0.1.6
!pip install python-docx
!pip install azure-core==1.30.0
!pip install azure-search-documents==11.4.0
!pip install pymupdf
!pip install pymupdf4llm
!pip install python-pptx
!pip install openai
```

The requirements for running the actual chatbot depend on what you already have installed, but the general list can be found below.

```python
pip install langchain
pip install streamlit
pip install azure-search
pip install openai
pip install streamlit-chat
pip install langchain-core
pip install azure-identity
```

## Index creation

A search index for your data can be created using the "create_Index" file (currently only PDFs, Word, Excel, and Powerpoint are supported).

After entering all the necessary credentials, the fields for your index. The type of vector and semantic search you want to use can be done here.
```python
fields = [
    SearchField(name="filepath", type=SearchFieldDataType.String, filterable=True, sortable=True),
    SearchField(name="summary", type=SearchFieldDataType.String),
    SearchField(name="chunk_id", type=SearchFieldDataType.String,key=True),
    SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
    SearchField(name="id", type=SearchFieldDataType.String),
    SearchField(name="file_name", type=SearchFieldDataType.String),
    SearchField(name="sap_number", type=SearchFieldDataType.String),
    SearchField(name="year", type=SearchFieldDataType.String),
    SearchField(name="status", type=SearchFieldDataType.String),
    SearchField(name="description", type=SearchFieldDataType.String),
    SearchField(name="Publication_Type", type=SearchFieldDataType.String),
    SearchField(name="Model_Tag", type=SearchFieldDataType.String),
    SearchField(name="meta_content", type=SearchFieldDataType.String),
    SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
    SearchField(name="meta_content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile")
]

# Configure vector search
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(
            name="myHnsw",
            parameters=HnswParameters(
                m=4,
                ef_construction=100,
                ef_search=100,
                metric=VectorSearchAlgorithmMetric.COSINE
            )
        )
    ],
    profiles=[
        VectorSearchProfile(
            name="myHnswProfile",
            algorithm_configuration_name="myHnsw"
        )
    ]
)

# Configure semantic search
semantic_config = SemanticConfiguration(
    name="my-semantic-config",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[
            SemanticField(field_name="content"),
            SemanticField(field_name="filepath"),
            SemanticField(field_name="summary")
        ],
        keyword_field=SemanticField(field_name="content")
    )
)

index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
    semantic_search=SemanticSearch(configurations=[semantic_config])
)

# Create or update the search index
index_client.create_or_update_index(index)

```

Update the following code in the "process_document" function in order to match you index and meta data (meta data is not required).
```python
meta_content = (
                            f"File Name: {filename}, "
                            f"Sap Number: {meta_data.get('sap_number', '')}, "
                            f"Year: {meta_data.get('print_date', '')}, "
                            f"Status: {meta_data.get('status', '')}, "
                            f"Description: {meta_data.get('description', '')}, "
                            f"Publication Type: {meta_data.get('Publication_Type', '')}, "
                            f"Model Tag: {meta_data.get('Model_Tag', '')}"
                        )
                        chunk_id = f"{document_id}_{chunk_counter}"

                        document = {
                            "filepath": filepath,
                            "summary": summary,
                            "chunk_id": chunk_id,
                            "content": chunk,
                            "id": document_id,
                            "meta_content": meta_content,
                            "file_name": filename,
                            "sap_number": meta_data.get('sap_number', ''),
                            "year": meta_data.get('print_date', ''),
                            "status": meta_data.get('status', ''),
                            "description": meta_data.get('description', ''),
                            "Publication_Type": meta_data.get('Publication_Type', ''),
                            "Model_Tag": meta_data.get('Model_Tag', ''),
                            "contentVector": [],
                            "meta_content_vector": []
                        }
```

If you added more vector fields to your index, update the in the embedding cell here
```python

    for i, item in enumerate(input_data):
        item['contentVector'] = content_embeddings[i]
        #print(item['contentVector'])
        item['meta_content_vector'] = meta_content_embeddings[i]

    return input_data

def filter_documents_with_empty_vectors(documents):
    filtered_docs = []
    for doc in documents:
        content_vector = doc.get('contentVector', [])
        meta_content_vector = doc.get('meta_content_vector', [])
```

## Chatbot creation

Here we first define our fields for search, and the vectorizable fields. We also specify the type of embedding used in the index creation. 

The template used to prompt GPT for query and context analysis is also defined.

```python


index_name_pirl = "your_index"
select_fields_from_index_pirl = ["filepath", "content","chunk_id"]
vectorizable_fields_pirl = "contentVector, meta_content_vector"

#streamlit message
intro_msg = "Hello there! How may I assist you today?"
m_data = 'your_meta_data'  # meta data unique for each project
log_filename_table = "your_logs"


GPT_DEPLOYMENT_NAME = 'gpt-4o'
os.environ["AZURE_OPENAI_API_KEY"] = 'your_key'
os.environ["AZURE_OPENAI_ENDPOINT"] = "your_endpoint"
openai_api_version="2024-02-15-preview"

# New Azure search config
endpoint = "endpoint"
key_credential_azure_search = "your_credential"
credential_azure_search = AzureKeyCredential(key_credential_azure_search)

# New embedding OpenAI config
azure_openai_endpoint = "your_endpoint"
azure_openai_key = "your_key"
azure_openai_embedding_deployment = "text-embedding-ada-002"
azure_openai_api_version = "2024-02-15-preview" 


template = """

```

Here, the context labeling is done in order to rank results from the search based on their source. Other criteria may be used.
```python

    for result in results_main:
        #if result["filepath"].startswith('filepath1'):
        results_pirl.append({
                "filepath": result["filepath"],
                "content": result["content"],
                # "meta_content": result["meta_content"],
                # "status": result["status"],
                # "form_number": result["sap_number"]
            })
        # elif result["filepath"].startswith('filepath2'):
        #     results_scene7.append({
        #         "filepath": result["filepath"],
        #         "content": result["content"],
        #         "year": result["year"],
        #         "meta_content": result["meta_content"],
        #         "status": result["status"],
        #         "form_number": result["form_number"]
        #     })
        # elif result["filepath"].startswith('filepath3):
        #     results_archive.append({
        #         "filepath": result["filepath"],
        #         "content": result["content"],
        #         "year": result["year"],
        #         "meta_content": result["meta_content"],
        #         "status": result["status"],
        #         "form_number": result["form_number"]
        #     })

        pdf_retr.append(result["filepath"])
```
        

