<!-- section: answerable -->
You are grading one answer from a documentation assistant against a fixed ground truth.
Judge ONLY against the GROUND TRUTH and the CITED PASSAGES below. Do not use your own knowledge: a statement that is true in general but is not supported by the ground truth or the cited passages still counts as unsupported.
The answer may paraphrase, and it may be in another language than the ground truth (for example a Vietnamese answer to an English ground truth). Paraphrase and translation are fine; judge the meaning.

Grade as follows:
1. "required_points": one entry for EVERY required answer point listed below, with its exact "id". "covered" is "yes" if the answer states the point (or an acceptable variation of it), "partial" if it states only part of it or states it vaguely, "no" if it does not state it. Optional points are context only: do not list them.
2. "contradicts_ground_truth": true if the answer states something the ground truth contradicts, or states any MUST-NOT-CLAIM item; otherwise false.
3. "unsupported_claims": every substantive claim in the answer that neither the ground truth nor the cited passages support (quote it briefly). An empty list if there are none. Do not list claims that are only restated more loosely.
4. "citations": one entry for EVERY citation marker listed under CITED PASSAGES, with its "marker" number. "supports_attached_claim" is "yes" if the passage supports the claim(s) the marker is attached to in the answer, "partial" if it supports them only in part, "no" if it does not.
5. "reason": at most 2 sentences.

QUESTION:
{question}

GROUND TRUTH
Expected answer: {expected_answer}
Answer points:
{answer_points}
Acceptable variations:
{acceptable_variations}
MUST-NOT-CLAIM:
{must_not_claim}
Citation criteria:
{citation_criteria}

ANSWER TO GRADE:
{answer}

Note the assistant added about missing information:
{missing_information}

CITED PASSAGES (the full text the answer's markers point to):
{cited_passages}
<!-- section: refusal -->
You are checking one response from a documentation assistant to a question that its document collection does NOT answer. The correct behaviour is to say that the documents do not cover the topic. Mentioning related content from the documents is fine, as long as the response says the topic isn't covered and does not present that content as the answer.
Judge ONLY the RESPONSE, the NOTE and the CITED PASSAGES below, against the rules given here. Do not use your own knowledge about the topic.
The response may be in another language than these instructions; judge the meaning.

Set "presents_related_as_answer" to true if ANY of these holds:
- the response or the note presents related content from the documents as the answer to the question;
- it presents an inferred or adapted technique as what the documents say to do;
- it makes a substantive claim that answers the question (supported by the documents or not);
- it does not say that the documents don't cover the question (or don't contain enough information).
Otherwise set it to false.
Example (made up): the question asks how to encrypt a message queue, and the documents only describe message queues. "The documents don't explain queue encryption; they describe queue creation [1]" → false. "To encrypt the queue, create it with the secure option [1]" → true.
"reason": at most 2 sentences.

QUESTION:
{question}

Expected behaviour: {expected_answer}
Acceptable variations:
{acceptable_variations}
MUST-NOT-CLAIM:
{must_not_claim}
Citation criteria:
{citation_criteria}

The assistant marked its response as insufficient: {insufficient}

RESPONSE:
{answer}

NOTE (what the assistant said is missing):
{missing_information}

CITED PASSAGES (related content the response points to):
{cited_passages}
