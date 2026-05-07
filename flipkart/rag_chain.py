
from langchain_groq import ChatGroq

# UPDATED IMPORTS FOR LANGCHAIN 1.x
from langchain_classic.chains import (
    create_history_aware_retriever,
    create_retrieval_chain,
)

from langchain_classic.chains.combine_documents import (
    create_stuff_documents_chain,
)

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_community.chat_message_histories import (
    ChatMessageHistory,
)

from langchain_core.chat_history import BaseChatMessageHistory

from flipkart.config import Config


class RAGChainBuilder:

    def __init__(self, vector_store):

        self.vector_store = vector_store

        self.model = ChatGroq(
            model=Config.RAG_MODEL,
            temperature=0.2
        )

        self.history_store = {}

    def _get_history(
        self,
        session_id: str
    ) -> BaseChatMessageHistory:

        if session_id not in self.history_store:
            self.history_store[session_id] = ChatMessageHistory()

        return self.history_store[session_id]

    def build_chain(self):

        retriever = self.vector_store.as_retriever(
            search_kwargs={"k": 3}
        )

        # CONTEXTUALIZATION PROMPT
        context_prompt = ChatPromptTemplate.from_messages([

            (
                "system",
                """
Given the chat history and latest user question,
rewrite the question as a standalone question.

Do NOT answer the question.
Only rewrite it if needed.
"""
            ),

            MessagesPlaceholder(
                variable_name="chat_history"
            ),

            (
                "human",
                "{input}"
            )
        ])

        # MAIN QA PROMPT
        qa_prompt = ChatPromptTemplate.from_messages([

            (
                "system",
                """
You are an intelligent e-commerce recommendation assistant.

Use ONLY the provided context to answer.

========================
RESPONSE RULES
========================

- Give responses in neat formatted points.
- Use bullet points or numbering.
- Keep each recommendation separate.
- Mention product name first.
- Mention key features clearly.
- Keep answers concise and readable.
- Avoid large paragraphs.
- Use emojis where suitable.
- Do NOT hallucinate products outside context.
- If context is insufficient, say:
  "I couldn't find enough information in the reviews."

========================
RESPONSE FORMAT
========================

🎧 Product Name

- Feature 1
- Feature 2
- Feature 3

⭐ Why Recommended:
Short recommendation reason.

💰 Best For:
Gaming / Music / Calls / Budget / Premium

--------------------------------------------------

CONTEXT:
{context}

QUESTION:
{input}
"""
            ),

            MessagesPlaceholder(
                variable_name="chat_history"
            ),

            (
                "human",
                "{input}"
            )
        ])

        # HISTORY AWARE RETRIEVER
        history_aware_retriever = create_history_aware_retriever(
            self.model,
            retriever,
            context_prompt
        )

        # DOCUMENT QA CHAIN
        question_answer_chain = create_stuff_documents_chain(
            self.model,
            qa_prompt
        )

        # FINAL RAG CHAIN
        rag_chain = create_retrieval_chain(
            history_aware_retriever,
            question_answer_chain
        )

        # CHAT HISTORY WRAPPER
        conversational_rag_chain = RunnableWithMessageHistory(

            rag_chain,

            self._get_history,

            input_messages_key="input",

            history_messages_key="chat_history",

            output_messages_key="answer"
        )

        return conversational_rag_chain

