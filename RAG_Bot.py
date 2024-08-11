import streamlit as st
import requests
import streamlit_chat
import socket
import time
import os,io 
import json
import base64
import random
import threading
from io import BytesIO
import pandas as pd
from streamlit_chat import message
import azure
import azure.storage
from azure.storage.blob import BlobServiceClient, BlobClient, ContentSettings
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
#openai llm dependencies
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from langchain.prompts.prompt import PromptTemplate
# azure search dependencies
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType
from azure.search.documents.models import VectorFilterMode
from azure.search.documents import SearchIndexingBufferedSender
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
import pytz

st.set_page_config(layout="wide") #,initial_sidebar_state="expanded"

#################unique codes##################################################################################################################################

global select_fields_from_index, index_name, vectorizable_fields, intro_msg, llm, credential_blob, container_name, storage_account_name, log_filename_table

# storage_account_name"
storage_account_name = "your_storage_account"
 
# container_name = "librain-demo"
container_name = "your_container"

# credential_blob = DefaultAzureCredential(exclude_environment_credential = True) #Azure app
credential_blob= "your_credential" #Local

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

**Role and Context:**  
- Role: Conversational Technical Support Agent  
- Main Task: Troubleshoot technical issues and lookup for answers in documents 
- Chat History: `<chat_history>{chat_history}</chat_history>` 
- Contexts for the 3 sources
   
**Communication Style:**  
- Speak as a customer support agent  

**Source Contexts:**
- You are provided context from up to three different sources for each query
- Each source's context will be clearly labeled and separated for your evaluation.

**Evaluation of Sources**:
- Carefully review the context provided by each source.
- Determine which source's context best matches the query and use that document to frame the answer.
- If the answer to the user question needs a combination of information from multiple documents or multiple sources, then combine the relevant information to present the accurate answer.

   
**Answering Questions:**  
- Question enclosed in: `<question></question>`  
- Provide short and concise responses 
   
**Troubleshooting Steps:**  
- For troubleshooting questions, ask for model number and serial number (proceed without if unavailable)  
- For queries having response in multiple similar documents, refer to the "Specific queries" section below on how to pick the right document
- Provide step by step response wherever possible. Otherwise generate a brief response.
- Direct to Technical Support if unable to solve or find a response or if conversation is going nowhere
   
**Rules (Strictly abide):** 

- ask follow up questions! especially if you need more information or clarification
- give your initial response, but make sure to ask follow up questions, or at least suggest that if the user wants more specific info, they should answer follow up questisons (based on the context of the current chat history)
- for example, if someone asks for information about some device, but in the context you see multiple different devices, ask the user which device they are talking about! 

**Structure:**   
<chat_history>{chat_history}</chat_history>  
<pirl_context>{context1}</context1>
<scene7_context>{context2}<context2>
<archive_context>{context3}<context3>
<question>{question}</question>

"""

###################common codes#################################################################################################################################

#col_l1, col_l2 = st.columns([1,2]) 
#with col_l2:
#    logo_image = "C:/Users/kb2149/Downloads/lib_logo.png"
#    st.image(logo_image, width=200)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": intro_msg}]

prompt_template = PromptTemplate.from_template(template)

llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    openai_api_version=openai_api_version,
    azure_deployment=GPT_DEPLOYMENT_NAME,
    temperature=0,
    streaming=True
)

client = AzureOpenAI(
    azure_deployment=azure_openai_embedding_deployment,
    api_version=azure_openai_api_version,
    azure_endpoint=azure_openai_endpoint,
    api_key=azure_openai_key,
    # azure_ad_token_provider=token_provider if not azure_openai_key else None
)

def ask_open_ai(query, chat_history):
    search_client2 = SearchClient(endpoint=endpoint, index_name=index_name_pirl, credential=credential_azure_search)

    #start_time = time.time()
    embedding = client.embeddings.create(
        input=query, model=azure_openai_embedding_deployment
    ).data[0].embedding

    vector_query2 = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=2,
        fields=vectorizable_fields_pirl,
        exhaustive=True,
    )

    results_main = search_client2.search(
        search_text=query,
        vector_queries=[vector_query2],
        select=select_fields_from_index_pirl,
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name='my-semantic-config',
        query_caption=QueryCaptionType.EXTRACTIVE,
        query_answer=QueryAnswerType.EXTRACTIVE,
        top=3,
        vector_filter_mode=VectorFilterMode.PRE_FILTER,
    )

    results_pirl = []
    results_scene7 = []
    results_archive = []
    pdf_retr = []

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
        # elif result["filepath"].startswith('filepath3'):
        #     results_archive.append({
        #         "filepath": result["filepath"],
        #         "content": result["content"],
        #         "year": result["year"],
        #         "meta_content": result["meta_content"],
        #         "status": result["status"],
        #         "form_number": result["form_number"]
        #     })

        pdf_retr.append(result["filepath"])

        

    
    prompt = prompt_template.format(
        chat_history=chat_history, pirl_context=results_pirl,scene7_context=results_scene7,archive_context=results_archive, question=query
    )

    #print(prompt)


    message = HumanMessage(content=prompt)
    # end_time = time.time()
    # print("Time taken:", end_time - start_time)

    pdf_retr = list(dict.fromkeys(pdf_retr))
    return pdf_retr, message
  

def get_response(message_stream):
    response = ""
    with st.spinner(f"Generating my response...."): 
        stream = llm.stream(message_stream.content)
        response = st.write_stream(stream)
    end_time = time.time()
    return response, end_time
    
# def upload_text_to_blob(df, container_name, blob_name):
#     stream = BytesIO()
#     df.to_csv(stream, index=False)
#     stream.seek(0)
#     blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=credential_blob)
#     blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
#     blob_client.upload_blob(stream, overwrite=True)

# def log_text(query,response,feedback,filename,timetaken):
#     blob_name = filename 
#     today = datetime.now(pytz.timezone('US/Central')).strftime('%m-%d-%Y-%H:%M:%S')
#     df = read_blob_df(container_name, blob_name)
#     df = add_row(df,today,query,response,feedback,timetaken)
#     # df['Feedback category'] = df['Feedback'].apply(lambda x: x[:4])
#     df.drop_duplicates(subset=['Query','Response','Time Taken'], keep='last', inplace=True)
#     upload_text_to_blob(df, container_name, blob_name)


# def edit_stream_response(prompt,stream_response,feedback,timetaken):
#     with st.sidebar:
#         if stream_response:
#             log_text(prompt,stream_response,feedback,log_filename_table,timetaken) # comment out to get rid of feedback
#             st.success('Your feedback was recorded successfully.')
#             st.session_state.holder_text = ""
#             return 1
        
# def read_blob_df(container_name, blob_name):
#     blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=credential_blob)
#     blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
#     try:
#         blob_data = blob_client.download_blob()
#         blob_bytes = blob_data.readall()
#         with BytesIO(blob_bytes) as bio:
#             df = pd.read_csv(bio)
#         return df
#     except Exception as e:
#         print(f"Error reading blob: {str(e)}")
#         return None
    
# def add_row(df,timestamp,query,response,feedback,timetaken):
#     current_length = len(df)
#     df.loc[current_length] = [timestamp,query,response,feedback,timetaken]    
#     return df
    
# def load_blob_data(storage_account_name,container_name,blob_name):
#     blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=credential_blob)
#     container_client = blob_service_client.get_container_client(container_name)
#     blob_client = container_client.get_blob_client(blob_name)
#     blob_data = blob_client.download_blob()
#     pdf_content = blob_data.content_as_bytes()
#     pdf_b64 = base64.b64encode(pdf_content).decode("utf-8")
#     b_name = blob_name.split('/')[-1]
#     download_link = f'<a href="data:application/octet-stream;base64,{pdf_b64}" download="{b_name}">{b_name}</a>'
#     st.markdown(download_link, unsafe_allow_html=True)

# def load_meta_data(storage_account_name,container_name,blob_name):
#     blob_service_client = BlobServiceClient(account_url=f"https://{storage_account_name}.blob.core.windows.net", credential=credential_blob)
#     blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
#     blob_data = blob_client.download_blob()
#     blob_bytes = blob_data.readall()

#     # Read the blob bytes into a DataFrame
#     with BytesIO(blob_bytes) as bio:
#         df = pd.read_csv(bio)
#     return df

# def get_pdf(pdf_retr,pirl_lookup,meta_info):
#     with st.sidebar:
#         with st.spinner(f"Retrieving relevant documents..."): 
#             if pdf_retr:
#                 st.markdown("**Citation:**")
#                 for f in pdf_retr:
            
#                     if f.split('/')[-1] in pirl_lookup.keys():
#                         ff = f.split('/')[-1]
#                         fname1 = pirl_lookup[ff].split('/')[-1]
#                         desc = meta_info[meta_info["file_name"] == fname1]["description"].iloc[0]
#                         pub = meta_info[meta_info["file_name"] == fname1]["Publication_Type"].iloc[0]
#                         year = meta_info[meta_info["file_name"] == fname1]["print_date"].iloc[0].split(' ')[0]
#                         st.markdown(f'<a href="{pirl_lookup[ff]}" target="_blank">{fname1}</a>', unsafe_allow_html=True)
#                         st.markdown(f' - Publication Type: {pub}')
#                         st.markdown(f' - Description: {desc}')
#                         st.markdown(f' - Print Year: {year}')

#                     else:
#                         load_blob_data(storage_account_name,container_name,f)#'icomforts30datashareprod',"testdata",f) 
           
# if 'explanation' not in st.session_state:
#         st.session_state.explanation = ''
if 'prompt' not in st.session_state:
        st.session_state.prompt = ''
if 'response' not in st.session_state:
        st.session_state.response = ''
if 'end_time' not in st.session_state:
        st.session_state.end_time = 0
if 'tt' not in st.session_state:
        st.session_state.tt = 0   
if 'text_value' not in st.session_state:
        st.session_state.text_value = ""    
if 'explanation' not in st.session_state:
        st.session_state.explanation = ""    

def update():
    st.session_state.text += st.session_state.text_value

def get_response_followUp(message_stream):
    response = ""
    with st.spinner(f"Generating my response...."): 
        stream = llm.stream(message_stream.content)
        for chunk in stream:
           response += chunk.content
    return response

def create_follow_up_analysis_template(chat_history, query):
    templateFollowUp = """
    You are an AI assistant. You will analyze the following chat history and the current user input question. 
    Your tasks are:
    1. Identify if there is a follow-up question asked by the assistant in the chat history.
    2. Determine if the current  user input question is relevant to the detected follow-up question.
    3. Construct a new prompt using the relevant parts of the chat history and the current user input question. 
       If there is no follow-up question or if the user input question is not relevant, return the original user input question.
    4. Return it in a format that can be used by Azure cognitive search for finding information in an index.
    5. Only return the new prompt, do not print out your analysis or anything else.
    6. Return it as a string with nothing else surrounding the new prompt.
    7): Only include relevant parts of the chat history in the new query, don't append 
        things which aren't relevant to the detected follow up question. Don't try to 
        fill in information with things in previous chats when you aren't sure.

        **** VERY IMPORTANT *****
    8): If you see a vague question from the user, but no follow up question for it in the chat history, DO NOT 
        fill in the missing parts of the prompt with things from chat history. You haven't been given that information yet.

                Example: If the user asks, "What are the the specifications of a certain model Y, and the assistant replies something like "Could you please provide me more information such as the serial number"
                    you should detect that there is a follow up question, and if the user replies to the follow up with the "This is the serial number: XXXX"
                    you should detect that it's relevant to the follow up, and thus return the relevant parts of the chat history
                    In this case, the model name "Y" and the serial number "XXXX" should be returned by you. 
    
    Chat History: <chat_history>{chat_history}</chat_history>
    Current User Input Question: <question>{question}</question>
    """
    prompt_template = PromptTemplate.from_template(templateFollowUp)
    prompt = prompt_template.format(chat_history=chat_history, question=query)
    template = HumanMessage(content=prompt)
    return template

def main():
    # Display the chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    pdf_retr = []

    # Accept user input
    
    if prompt := st.chat_input("Type your question here."):

        start_time = time.time()
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
            #st.info( "Warning: Please take the results with a grain of salt. The information provided may not be completely accurate or up-to-date. Always verify critical details independently.")

        follow_up_analysis_prompt = create_follow_up_analysis_template(st.session_state.messages[-2:], prompt)
        analysis_response = get_response_followUp(follow_up_analysis_prompt)

        # Prepare for the assistant response
        assistant_placeholder = st.empty()
        with assistant_placeholder.container():
            with st.chat_message("assistant"):
                with st.spinner(f"Looking up my references...."):
                    pdf_retr, message_stream = ask_open_ai(analysis_response, st.session_state.messages[-6:])
                # get_pdf(pdf_retr, pirl_lookup, meta_info)  # Step 1: Retrieve file

                # Generate the assistant response
                response, end_time = get_response(message_stream)  # Step 2: Stream response

                # Update session state
                st.session_state.prompt = prompt
                st.session_state.response = response
                st.session_state.end_time = end_time
                st.session_state.start_time = start_time

                # Update the assistant message in the placeholder
                # assistant_placeholder.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

        if response:
            timetaken = end_time - start_time
            st.session_state.tt = timetaken
        
            # log_text(prompt, response, "No Feedback", log_filename_table, st.session_state.tt)

    # # Display feedback options in the sidebar
    # with st.sidebar:
    #     prompt = st.session_state.get('prompt', '')
    #     response = st.session_state.get('response', '')
    #     timetaken = st.session_state.get('tt', 0)
    #     st.markdown("--------------------------------------")
    #     st.markdown("**Did you find the response helpful?**")
    #     col1, col2, col3, col4 = st.columns([2.1, 2.1, 1.3, 1.3])
    #     st.button('Yes', on_click=edit_stream_response, args=[prompt, response, "Pass", timetaken])  
    #     explanation = st.text_input("If \"No\", please enter the right response...", placeholder="Type here...", max_chars=1000, label_visibility="visible")
        
    #     if st.button("Submit"):
    #         edit_stream_response(prompt, response, "Fail-" + explanation, timetaken)
        
    #     st.markdown("--------------------------------------")
if __name__ == "__main__":
    main()
