
const questionForm = document.getElementById("question-form");
const questionInput = document.getElementById("question");
const submitButton = document.getElementById("submit-button");
const characterCount = document.getElementById("character-count");

const loading = document.getElementById("loading");
const responseSection = document.getElementById("response-section");
const responseStatus = document.getElementById("response-status");
const answerText = document.getElementById("answer-text");

const sourcesSection = document.getElementById("sources-section");
const sourcesList = document.getElementById("sources-list");

const excerptSection = document.getElementById("excerpt-section");
const excerptText = document.getElementById("excerpt-text");

const errorMessage = document.getElementById("error-message");


/* Update the character count */

questionInput.addEventListener("input", () => {
    characterCount.textContent =
        `${questionInput.value.length} / 1000`;
});


/* Display an error message */

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove("hidden");
}


/* Reset previous response */

function resetResponse() {
    responseSection.classList.add("hidden");
    sourcesSection.classList.add("hidden");
    excerptSection.classList.add("hidden");
    errorMessage.classList.add("hidden");

    sourcesList.replaceChildren();
    answerText.textContent = "";
    excerptText.textContent = "";
}


/* Display source references safely */

function displaySources(sources) {

    sourcesList.replaceChildren();

    if (!sources || sources.length === 0) {
        sourcesSection.classList.add("hidden");
        return;
    }

    sources.forEach((source) => {

        const card = document.createElement("div");
        card.className = "source-card";

        const details = [
            ["Document", source.document_number],
            ["Revision", source.revision],
            ["Page", source.page_number],
            ["File", source.source_file]
        ];

        details.forEach(([label, value]) => {

            const paragraph = document.createElement("p");
            const strong = document.createElement("strong");

            strong.textContent = `${label}: `;
            paragraph.appendChild(strong);
            paragraph.appendChild(
                document.createTextNode(String(value))
            );

            card.appendChild(paragraph);
        });

        sourcesList.appendChild(card);
    });

    sourcesSection.classList.remove("hidden");
}


/* Display the generated answer */

function displayResponse(data) {

    answerText.textContent = data.answer || "No answer was returned.";

    if (data.status === "answered") {

        responseStatus.textContent = "Supported by SOP";
        responseStatus.className = "response-status";

    } else if (data.status === "insufficient_information") {

        responseStatus.textContent = "Insufficient information";
        responseStatus.className = "response-status warning";

    } else {

        responseStatus.textContent = "Response";
        responseStatus.className = "response-status warning";
    }

    displaySources(data.sources);

    if (
        data.supporting_excerpt &&
        data.status === "answered"
    ) {
        excerptText.textContent = data.supporting_excerpt;
        excerptSection.classList.remove("hidden");
    } else {
        excerptSection.classList.add("hidden");
    }

    responseSection.classList.remove("hidden");
}


/* Submit the question to FastAPI */

questionForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    const question = questionInput.value.trim();

    if (question.length < 3) {
        showError("Please enter a question containing at least 3 characters.");
        return;
    }

    if (question.length > 1000) {
        showError("Your question cannot exceed 1000 characters.");
        return;
    }

    resetResponse();

    loading.classList.remove("hidden");
    submitButton.disabled = true;
    questionInput.disabled = true;

    try {

        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const data = await response.json();

        if (!response.ok) {

            const detail = data.detail;

            if (
                response.status === 503 ||
                (detail && detail.status === "service_unavailable")
            ) {
                throw new Error(
                    "The AI service is temporarily unavailable. Please try again shortly."
                );
            }

            throw new Error(
                typeof detail === "string"
                    ? detail
                    : "Unable to process your question."
            );
        }

        displayResponse(data);

    } catch (error) {

        showError(
            error.message ||
            "Unable to connect to the application. Please try again."
        );

    } finally {

        loading.classList.add("hidden");
        submitButton.disabled = false;
        questionInput.disabled = false;
        questionInput.focus();
    }
});
