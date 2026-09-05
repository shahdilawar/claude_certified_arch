from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from pydantic import Field

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

@mcp.tool(
    name = "read_doc", 
    description = "Read the contents of a document by its ID.",
    )
def read_doc(
    doc_id: str = Field(description="The ID of the document to read")
    ) -> str:

    if doc_id not in docs:
        raise ValueError(f"Document not found: {doc_id}")
    return docs[doc_id]

@mcp.tool(
    name = "edit_document", 
    description = "Edit the contents of the document by the ID"
)
def edit_document(
    doc_id: str = Field(description="The ID of the document to edit"),
    old_str:str = Field(description="The string to be replaced in the document"),
    new_str:str = Field(description="The string to replace the old string with")
    ) -> str:

    if doc_id not in docs:
        raise ValueError(f"document with {doc_id} not in docs")

    docs[doc_id] = docs[doc_id].replace(old_str, new_str)

    return docs[doc_id]

@mcp.resource(
    "docs://documents", 
    mime_type="application/json",
    description="A resource that returns all document IDs."
)
def list_docs() -> list[str]:   
    return list(docs.keys())
# TODO: Write a resource to return the contents of a particular doc
@mcp.resource(
    "docs://documents/{doc_id}", 
    mime_type="text/plain",
    description="A resource that returns the contents of a particular document by its ID."
)
def get_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Document not found: {doc_id}")
    return docs[doc_id]
# TODO: Write a prompt to rewrite a doc in markdown format
@mcp.prompt(    
    name="format_doc", 
    description="Rewrite the contents of a document in markdown format."
)
def format_doc(
    doc_id: str = Field(description="The ID of the document to format")
) -> list[base.Message]:
    if doc_id not in docs:
        raise ValueError(f"Document not found: {doc_id}")

    prompt = f"""
    Your goal is to reformat a document to be written with markdown syntax.

    The id of the document you need to reformat is:

    {doc_id}

    Add in headers, bullet points, tables, etc as necessary. Feel free to add in extra formatting.
    Use the 'edit_document' tool to edit the document. After the document has been reformatted...
    """
    return [base.UserMessage(prompt)]

# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
