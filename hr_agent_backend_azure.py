# load core modules
import pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chat_models import AzureChatOpenAI
from langchain.chains import RetrievalQA
import pandas as pd
from azure.storage.filedatalake import DataLakeServiceClient
from io import StringIO
from langchain.tools.python.tool import PythonAstREPLTool
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain import LLMMathChain

pinecone.init(
        api_key="<your pinecone api key>",  
        environment="your pinecone environment"  
) 

index_name = 'tk-policy'
index = pinecone.Index(index_name)

embed = OpenAIEmbeddings(
                deployment="<your deployment name>",
                model="text-embedding-ada-002",
                openai_api_key='<your azure openai api key>',
                openai_api_base="<your api base>",
                openai_api_type="azure",
            )

text_field = 'text'
vectorstore = Pinecone(
    index, embed.embed_query, text_field
)

llm = AzureChatOpenAI(    
    deployment_name="<your deployment name>", 
    model_name="gpt-35-turbo", 
    openai_api_key='<your openai api key>',
    openai_api_version = '2023-03-15-preview', 
    openai_api_base='<your api base>',
    openai_api_type='azure'
    )

timekeeping_policy = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(),
)

client = DataLakeServiceClient(
                               account_url="<you azure account storage url>",
                               credential="<your azure storage account keys>"
                              )
file = client.get_file_system_client("<your azure storage account name>") \
             .get_file_client("employee_data/employee_data.csv") \
             .download_file() \
             .readall() \
             .decode('utf-8') 

csv_file = StringIO(file) 
df = pd.read_csv(csv_file) # load employee_data.csv as dataframe
python = PythonAstREPLTool(locals={"df": df}) # set access of python_repl tool to the dataframe

csv_file = StringIO(file)
df = pd.read_csv(csv_file) # load employee_data.csv as dataframe
python = PythonAstREPLTool(locals={"df": df}) # set access of python_repl tool to the dataframe

# create calculator tool
calculator = LLMMathChain.from_llm(llm=llm, verbose=True)

user = 'Kennedy Antonio' # set user
df_columns = df.columns.to_list() # print column names of df

tools = [
    Tool(
        name = "Timekeeping Policies",
        func=timekeeping_policy.run,
        description="""
        Useful for when you need to answer questions about employee timekeeping policies.

        <user>: What is the policy on unused vacation leave?
        <assistant>: I need to check the timekeeping policies to answer this question.
        <assistant>: Action: Timekeeping Policies
        <assistant>: Action Input: Vacation Leave Policy - Unused Leave
        ...
        """
    ),
    Tool(
        name = "Employee Data",
        func=python.run,
        description = f"""
        Useful for when you need to answer questions about employee data stored in pandas dataframe 'df'. 
        Run python pandas operations on 'df' to help you get the right answer.
        'df' has the following columns: {df_columns}
        
        <user>: How many Sick Leave do I have left?
        <assistant>: df[df['name'] == '{user}']['sick_leave']
        <assistant>: You have n sick leaves left.              
        """
    ),
    Tool(
        name = "Calculator",
        func=calculator.run,
        description = f"""
        Useful when you need to do math operations or arithmetic.
        """
    )
]

# change the value of the prefix argument in the initialize_agent function. This will overwrite the default prompt template of the zero shot agent type
agent_kwargs = {'prefix': f'You are friendly HR assistant. You are tasked to assist the current user: {user} on questions related to HR. You have access to the following tools:'}


# initialize the LLM agent
agent = initialize_agent(tools, 
                         llm, 
                         agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
                         verbose=True, 
                         agent_kwargs=agent_kwargs
                         )
# define q and a function for frontend
def get_response(user_input):
    response = agent.run(user_input)
    return response