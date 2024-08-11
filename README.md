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
