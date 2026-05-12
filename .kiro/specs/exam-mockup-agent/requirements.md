# Requirements Document

## Introduction

This feature implements a cloud provider certification exam mockup agent deployable on Amazon Bedrock AgentCore. The agent allows users to upload XLSX files containing exam questions (with multiple-choice answers), practice in two modes (Practice and Timed), and leverage AI to explain correct answers. The system supports local deployment for UI validation before cloud deployment.

## Glossary

- **Exam_Agent**: The AI-powered agent system that manages exam sessions, presents questions, and provides answer explanations
- **XLSX_File**: An Excel spreadsheet file containing exam questions, possible answers, correct answer indicators, and question type metadata
- **Practice_Mode**: An untimed exam mode where users answer questions at their own pace with immediate feedback
- **Timed_Mode**: A 120-minute exam session presenting 60 randomly selected questions with a countdown timer
- **Question_Bank**: The parsed and stored collection of questions extracted from an uploaded XLSX file
- **Multiple_Choice_Question**: A question that requires selecting more than one correct answer from the available options
- **Single_Choice_Question**: A question that requires selecting exactly one correct answer from the available options
- **Exam_Session**: A stateful interaction representing one attempt at answering questions in either mode
- **AI_Explanation**: An AI-generated detailed explanation of why the correct answer is correct and why other options are incorrect
- **Answer_Shuffling**: The randomization of answer option order when presenting questions to prevent memorization of option positions
- **Pass_Threshold**: The minimum percentage score (72%) required to pass the exam simulation

## Requirements

### Requirement 1

**User Story:** As a certification candidate, I want to upload an XLSX file containing exam questions, so that I can use my own question sets for practice.

#### Acceptance Criteria

1. WHEN a user uploads a valid XLSX file THEN the Exam_Agent SHALL parse the file and store all questions in the Question_Bank
2. WHEN the XLSX file contains questions with 4 or more possible answers THEN the Exam_Agent SHALL preserve all answer options and their correct/incorrect designations
3. WHEN the XLSX file contains multiple-choice questions THEN the Exam_Agent SHALL identify and store multiple correct answers for that question
4. IF a user uploads an invalid or corrupted XLSX file THEN the Exam_Agent SHALL reject the upload and display a descriptive error message indicating the issue
5. IF a user uploads an XLSX file with missing required columns THEN the Exam_Agent SHALL reject the upload and specify which columns are missing
6. WHEN the Exam_Agent presents a question to the user THEN the Exam_Agent SHALL shuffle the order of answer options randomly while preserving the correct answer mapping

### Requirement 2

**User Story:** As a certification candidate, I want to practice in an untimed mode, so that I can learn at my own pace without pressure.

#### Acceptance Criteria

1. WHEN a user selects Practice_Mode THEN the Exam_Agent SHALL present questions from the Question_Bank one at a time without a time constraint
2. WHEN a user submits an answer in Practice_Mode THEN the Exam_Agent SHALL immediately indicate whether the answer is correct or incorrect
3. WHEN a user completes a question in Practice_Mode THEN the Exam_Agent SHALL allow the user to proceed to the next question or revisit previous questions
4. WHEN a user finishes all questions in Practice_Mode THEN the Exam_Agent SHALL display a summary showing total correct answers, total incorrect answers, and percentage score

### Requirement 3

**User Story:** As a certification candidate, I want to take a timed exam simulation, so that I can prepare for the real exam conditions.

#### Acceptance Criteria

1. WHEN a user selects Timed_Mode THEN the Exam_Agent SHALL randomly select 60 questions from the Question_Bank and start a 120-minute countdown timer
2. WHILE the Exam_Session is in Timed_Mode THEN the Exam_Agent SHALL display the remaining time to the user continuously
3. WHEN the 120-minute timer expires THEN the Exam_Agent SHALL automatically end the Exam_Session and display the results
4. WHEN a user submits all 60 answers before the timer expires THEN the Exam_Agent SHALL end the Exam_Session and display the results
5. IF the Question_Bank contains fewer than 60 questions THEN the Exam_Agent SHALL use all available questions and inform the user of the reduced question count

### Requirement 4

**User Story:** As a certification candidate, I want AI-powered explanations for correct answers, so that I can understand the reasoning behind each answer.

#### Acceptance Criteria

1. WHEN a user requests an AI_Explanation for a question THEN the Exam_Agent SHALL generate a detailed explanation of why the correct answer is correct
2. WHEN the Exam_Agent generates an AI_Explanation THEN the Exam_Agent SHALL also explain why each incorrect option is wrong
3. WHEN a user is in Practice_Mode THEN the Exam_Agent SHALL offer the AI_Explanation option after each answer submission
4. WHEN a user is in Timed_Mode THEN the Exam_Agent SHALL offer AI_Explanation only after the Exam_Session ends in the results review

### Requirement 5

**User Story:** As a developer, I want to deploy and validate the agent locally first, so that I can test the UI and functionality before deploying to Amazon Bedrock AgentCore.

#### Acceptance Criteria

1. WHEN a developer runs the local deployment command THEN the Exam_Agent SHALL start a local web server serving the UI
2. WHEN the Exam_Agent runs locally THEN the Exam_Agent SHALL provide the same functionality as the cloud-deployed version
3. WHEN the local deployment is validated THEN the Exam_Agent SHALL be deployable to Amazon Bedrock AgentCore without code changes to the core logic

### Requirement 6

**User Story:** As a certification candidate, I want to see my exam results clearly with a pass/fail status, so that I can identify areas for improvement and know if I would have passed the real exam.

#### Acceptance Criteria

1. WHEN an Exam_Session ends THEN the Exam_Agent SHALL display the total score as a fraction and percentage
2. WHEN an Exam_Session ends THEN the Exam_Agent SHALL categorize results by showing which questions were answered correctly and which were answered incorrectly
3. WHEN reviewing results THEN the Exam_Agent SHALL allow the user to navigate to any question to see the selected answer and the correct answer
4. WHEN an Exam_Session ends THEN the Exam_Agent SHALL display a pass or fail status based on whether the score meets or exceeds the Pass_Threshold
5. WHEN a user clicks the submit button THEN the Exam_Agent SHALL display the results page showing pass/fail status, percentage score, and allow the user to review all submitted answers with correct/incorrect indicators

### Requirement 7

**User Story:** As a certification candidate, I want the XLSX file format to be clearly defined, so that I can prepare my question files correctly.

#### Acceptance Criteria

1. THE Exam_Agent SHALL accept XLSX files with columns: Question, Option_A, Option_B, Option_C, Option_D (and optionally Option_E, Option_F), Correct_Answer, and Question_Type
2. WHEN the Question_Type column value is "multiple" THEN the Exam_Agent SHALL treat the Correct_Answer column as a comma-separated list of correct option letters
3. WHEN the Question_Type column value is "single" THEN the Exam_Agent SHALL treat the Correct_Answer column as a single option letter

### Requirement 8

**User Story:** As a certification candidate, I want the agent to serialize and deserialize my exam session state, so that I can resume sessions or review past attempts.

#### Acceptance Criteria

1. WHEN an Exam_Session is active THEN the Exam_Agent SHALL serialize the session state to JSON format
2. WHEN a user resumes a session THEN the Exam_Agent SHALL deserialize the JSON state and restore the Exam_Session to its previous state
3. WHEN the Exam_Agent serializes then deserializes an Exam_Session THEN the restored session SHALL be equivalent to the original session (round-trip consistency)
