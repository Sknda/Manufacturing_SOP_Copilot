# Thinking and Design Reflection

## 1. Understanding the User

The primary user of this application is a manufacturing supervisor or production-floor employee who needs quick access to operational instructions when a production issue, machine alarm, quality concern or maintenance requirement occurs.

The user may not know which SOP or manual contains the required information. Searching through multiple PDF documents manually can take time, especially when production is delayed.

The copilot is intended to reduce the time required to locate relevant instructions while retaining the ability to verify the answer against the original document.

The application is not intended to replace the supervisor, maintenance technician, quality engineer or safety officer. It is an information-retrieval assistant that helps users locate and understand documented procedures.

## 2. Initial User Journey

My initial understanding of the user journey was:

1. Production units stop or experience delays because of an operational problem.
2. The supervisor opens the application and describes the problem.
3. The AI searches the manuals and provides a possible solution.
4. The supervisor trusts the response when it can be verified against the source manual.
5. If the answer is missing or unclear, the supervisor contacts the responsible department or person.

I also initially identified repeated questions as a possible source of hallucination.

On further consideration, repetition alone does not necessarily cause hallucinations. A more important risk is that the system may retrieve irrelevant, outdated or incomplete information and still generate a confident answer.

For this reason, the system needs to distinguish between an answer supported by the supplied documents and a question for which sufficient evidence is unavailable.

## 3. Why RAG?

A general-purpose language model may have broad knowledge, but it cannot be assumed to know an organization's internal manufacturing procedures.

Using a RAG architecture allows the application to retrieve relevant passages from the supplied SOPs and manuals before generating an answer.

The implementation follows this process:

1. Extract text from the supplied PDF documents.
2. Split the extracted text into manageable, overlapping chunks.
3. Generate embeddings for each chunk.
4. Store the embeddings in a FAISS index.
5. Convert the user's question into an embedding.
6. Retrieve the most relevant document chunks.
7. Provide the retrieved evidence to Gemini for answer generation.
8. Return the answer with source references and a supporting excerpt.

This approach keeps the answer connected to the supplied documents rather than relying solely on the model's general knowledge.

## 4. Key Design Decisions

### 4.1 Document processing and chunking

PyMuPDF is used to extract text page by page. Document metadata includes document number, revision, effective date, source filename and page number.

The extracted content is split into chunks with overlap so that information near chunk boundaries is less likely to lose its context.

A limitation is that PDF tables may not always extract in their original visual structure. This can affect how sampling tables and measurement specifications are represented to the retrieval system.

### 4.2 Embeddings and retrieval

I selected Gemini's `gemini-embedding-001` model to generate document and query embeddings.

FAISS is used for local vector similarity search. This avoids requiring a separate hosted vector database for the prototype.

The index uses normalized vectors and inner-product similarity. A retrieval threshold of 0.60 was selected after testing.

During testing, a question about the company's leave policy initially retrieved unrelated content at a lower threshold. Raising the threshold prevented those weak matches from being passed to the answer generator.

The threshold is a practical prototype setting, not a universally validated relevance boundary. It may need further calibration with a larger evaluation set.

### 4.3 Revision handling

The supplied documents contain both Revision 03 and Revision 04 of `QC-SOP-014`.

Revision 04 explicitly states that it supersedes Revision 03. I implemented this relationship in the version manager so that the older revision is excluded from the active retrieval index.

I chose an explicit supersession relationship rather than assuming that the highest revision number across all documents is always the correct one. Different document numbers can describe different procedures, and revision numbers should not be compared across unrelated documents.

The prototype only knows the documents and supersession information supplied with the assignment. It does not verify the latest revision against a live QMS.

### 4.4 Evidence-based answer generation

Gemini Flash is used to generate the final answer.

The answer-generation instructions require the model to:

- Use the retrieved document evidence.
- Avoid inventing values, procedures or instructions.
- Disclose when the retrieved evidence is insufficient or ambiguous.
- Identify the evidence used for the answer.
- Return a supporting excerpt.

The implementation validates evidence identifiers against the retrieved chunks and checks whether the returned excerpt is supported by the selected evidence.

### 4.5 Explicit no-answer behavior

The system should not answer every question simply because a language model can generate plausible text.

For example, the supplied manuals do not define the company's employee leave policy. The expected behavior is to state that the available documents do not contain that information.

This is important because an unsupported answer in a manufacturing environment could lead to incorrect operational decisions.

## 5. AI Critique and Iteration

I used AI assistance during implementation, but I treated the generated code and recommendations as proposals that needed to be tested.

A few examples of the iteration process:

**Retrieval quality**

The first retrieval threshold allowed unrelated chunks to appear for an unsupported question. I examined the similarity scores and increased the threshold from 0.35 to 0.60. The leave-policy question then returned no sufficiently relevant chunks.

This reinforced that a RAG system needs an explicit relevance check; merely retrieving the nearest chunks does not mean they are relevant enough to support an answer.

**Model availability**

The Gemini API returned model availability and temporary service errors during development. I tested an available Flash model and added retry handling for temporary failures and rate limits.

This made the application more resilient to transient API problems, although it cannot eliminate quota or service-availability constraints.

**Source verification**

A generated answer is not sufficient by itself. The source document, revision and page number need to be visible so that the user can inspect the original instruction.

I therefore included source references and supporting excerpts in the API response and frontend.

**Testing unsupported questions**

The leave-policy question was useful because it tested whether the application could decline to answer when the supplied documents did not contain the requested information.

The desired outcome was an explicit insufficient-information response rather than a plausible but unsupported answer.

## 6. Improvement Selected from the User Journey

The most important improvement I chose was to make the answer verifiable and to provide an explicit fallback when the evidence is missing.

The initial journey emphasized that a supervisor would trust an answer if there was proof that it came from a manual.

I translated this into three application behaviors:

1. Display the source document and revision.
2. Display the relevant page number and supporting excerpt.
3. Return an insufficient-information response when the retrieval stage does not find sufficiently relevant evidence.

This improves traceability and gives the user a clear next step when the system cannot answer.

For safety-related procedures, the user should still consult the applicable controlled SOP and follow the organization's escalation process.

## 7. Current Limitations

The current prototype has several limitations:

- It uses only the four supplied PDF documents.
- It does not connect to a live QMS or verify document approval status.
- Retrieval quality depends on PDF extraction, chunking and the selected similarity threshold.
- Table-heavy documents may require more specialized extraction.
- Gemini API calls require internet connectivity and are subject to quotas and rate limits.
- Repeated questions currently make API calls; local embedding and answer caching have not yet been implemented.
- The application has not been validated for real production or safety-critical use.

These limitations are important when considering whether the prototype could be used in an actual manufacturing environment.

## 8. Final Reflection

The main learning from this assignment was that building a useful AI copilot involves more than connecting a language model to a collection of documents.

The quality of the system depends on document processing, retrieval relevance, revision awareness, answer constraints and the ability to communicate uncertainty.

I initially focused on getting the application to retrieve and generate answers. Testing showed that the system also needed to recognize when the retrieved content was not relevant enough and when it should abstain.

I also learned that source traceability is particularly important in manufacturing workflows. A supervisor should be able to inspect the document and revision behind an answer rather than relying on the model's response alone.

The current implementation is a working prototype. Further improvements would include better table extraction, broader evaluation, API usage optimization through caching and integration with an approved document-control system.

My overall goal was to build an assistant that helps users find documented information faster without presenting unsupported AI-generated instructions as established procedures.