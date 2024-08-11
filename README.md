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
