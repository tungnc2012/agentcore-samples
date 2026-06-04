# Implementation Plan

- [x] 1. Set up project structure and dependencies






  - Create directory structure: `exam_mockup_agent/` with `parser.py`, `session.py`, `scorer.py`, `agent.py`, `app.py`
  - Create `tests/` directory with `conftest.py`, `test_parser.py`, `test_session.py`, `test_scorer.py`
  - Create `requirements.txt` with: streamlit, openpyxl, strands-agents, hypothesis, pytest, boto3
  - Create `README.md` with setup and run instructions
  - _Requirements: 5.1, 5.2_

- [x] 2. Implement data models and XLSX parser






  - [x] 2.1 Create data models (`models.py`)

    - Implement `Question` dataclass with fields: id, text, options (dict), correct_answers (list), question_type
    - Implement `ExamSession` dataclass with serialization/deserialization methods
    - Implement `ExamResult` and `QuestionResult` dataclasses
    - _Requirements: 7.1, 8.1, 8.2_

  - [x] 2.2 Implement XLSX parser (`parser.py`)

    - Implement `validate_xlsx_structure()` to check required columns and return missing ones
    - Implement `parse_xlsx()` to read XLSX and return list of Question objects
    - Handle optional columns (Option_E, Option_F)
    - Parse Correct_Answer as single letter or comma-separated list based on Question_Type
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.2, 7.3_

  - [x] 2.3 Implement XLSX writer utility (`writer.py`) for testing round-trips

    - Implement `write_xlsx(questions: list[Question], file_path: str)` to write questions back to XLSX format
    - _Requirements: 1.1 (enables round-trip testing)_
  - [ ]* 2.4 Write property test: XLSX Parsing Round-Trip
    - **Property 1: XLSX Parsing Round-Trip**
    - **Validates: Requirements 1.1, 1.2, 1.3, 7.1, 7.2, 7.3**
    - Use Hypothesis to generate random valid Question lists, write to XLSX, parse back, assert equivalence
  - [ ]* 2.5 Write property test: Invalid XLSX Rejection
    - **Property 2: Invalid XLSX Rejection with Column Identification**
    - **Validates: Requirements 1.5**
    - Use Hypothesis to generate XLSX files with random subsets of required columns removed, verify error contains missing column names

- [x] 3. Implement session management





  - [x] 3.1 Implement session creation and management (`session.py`)

    - Implement `create_practice_session(questions)` - includes all questions, duration=0
    - Implement `create_timed_session(questions, count=60)` - randomly selects min(60, len(questions)), duration=120
    - Implement `submit_answer(session, question_id, selected_answers)` to record answers
    - Implement `is_time_expired(session)` to check if timed session has exceeded duration
    - _Requirements: 2.1, 3.1, 3.5_
  - [x] 3.2 Implement session serialization (`models.py` serialize/deserialize methods)


    - Implement `ExamSession.serialize()` returning JSON string
    - Implement `ExamSession.deserialize(json_str)` class method returning ExamSession
    - Handle datetime serialization as ISO format strings
    - _Requirements: 8.1, 8.2, 8.3_
  - [ ]* 3.3 Write property test: Session Creation Invariants
    - **Property 3: Session Creation Invariants**
    - **Validates: Requirements 2.1, 3.1, 3.5**
    - Use Hypothesis to generate question banks of varying sizes, verify timed selects min(60, N) with duration=120, practice includes all with duration=0
  - [ ]* 3.4 Write property test: Session Serialization Round-Trip
    - **Property 5: Session Serialization Round-Trip**
    - **Validates: Requirements 8.1, 8.2, 8.3**
    - Use Hypothesis to generate random valid ExamSession objects, serialize then deserialize, assert equivalence

- [x] 4. Implement answer shuffling and scoring engine





  - [x] 4.1 Implement answer option shuffling (`session.py`)


    - Implement `shuffle_options(question: Question) -> list[str]` to return a random permutation of option keys
    - Add `shuffled_options` field to `ExamSession` model (dict[int, list[str]])
    - Generate shuffled option orders for each question during session creation
    - Update `serialize()`/`deserialize()` to include `shuffled_options`
    - _Requirements: 1.6_
  - [ ]* 4.2 Write property test: Answer Shuffling Preserves Content
    - **Property 6: Answer Shuffling Preserves Content**
    - **Validates: Requirements 1.6**
    - Use Hypothesis to generate random Questions, shuffle options, verify the shuffled keys are a permutation of the original keys (same set, same size)
  - [x] 4.3 Implement scoring logic (`scorer.py`)


    - Implement `calculate_score(session)` returning ExamResult
    - A question is correct if and only if selected answers exactly match correct answers (order-independent)
    - Calculate percentage as (correct_count / total_questions) * 100
    - Determine pass/fail: passed = True if score_percentage >= 72.0
    - Generate per-question QuestionResult breakdown
    - _Requirements: 2.2, 2.4, 6.1, 6.2, 6.4_
  - [ ]* 4.4 Write property test: Scoring Correctness
    - **Property 4: Scoring Correctness**
    - **Validates: Requirements 2.2, 2.4, 6.1, 6.2, 6.4**
    - Use Hypothesis to generate completed sessions with random answers, verify correct + incorrect = total, percentage math, per-question categorization, and passed == (score_percentage >= 72.0)
  - [ ]* 4.5 Write property test: Pass/Fail Threshold Consistency
    - **Property 7: Pass/Fail Threshold Consistency**
    - **Validates: Requirements 6.4**
    - Use Hypothesis to generate ExamResults with varying percentages, verify passed is True iff score_percentage >= 72.0

- [x] 5. Checkpoint - Make sure all tests are passing





  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement AI explanation agent






  - [x] 6.1 Implement explanation agent (`agent.py`)

    - Set up Strands Agent with Bedrock Claude model
    - Implement `explain_answer(question, selected_answers)` that prompts the LLM to explain why correct answers are correct and why incorrect options are wrong
    - Include system prompt guiding the agent to provide educational, certification-focused explanations
    - _Requirements: 4.1, 4.2_

- [x] 7. Implement Streamlit UI





  - [x] 7.1 Implement home page and file upload (`app.py`)


    - Create Streamlit app with file upload widget accepting .xlsx files
    - Display mode selection (Practice / Timed) after successful upload
    - Show validation errors if upload fails
    - _Requirements: 1.1, 1.4, 1.5, 5.1_

  - [x] 7.2 Implement Practice Mode UI






    - Display one question at a time with options in shuffled order (from session's shuffled_options)
    - Use radio buttons (single) or checkboxes (multiple) for answer selection
    - Show immediate correct/incorrect feedback after answer submission
    - Add "Explain Answer" button that calls the AI agent
    - Add navigation (Next, Previous) buttons
    - Show progress indicator (question X of Y)

    - _Requirements: 1.6, 2.1, 2.2, 2.3, 4.3_
  - [x] 7.3 Implement Timed Mode UI






    - Display options in shuffled order (from session's shuffled_options)
    - Display countdown timer (120 minutes) in sidebar
    - Show question navigation panel
    - Auto-submit when timer expires

    - Allow manual submission before timer expires

    - _Requirements: 1.6, 3.1, 3.2, 3.3, 3.4_

  - [x] 7.4 Implement Results page




    - Display pass/fail status banner (green PASSED or red FAILED)
    - Display total score as fraction and percentage
    - Show per-question breakdown (correct/incorrect indicators)
    - Allow clicking any question to see selected vs correct answer
    - Add "Explain" button per question (calls AI agent)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 4.4_

- [x] 8. Implement AgentCore deployment wrapper





  - [x] 8.1 Create AgentCore entrypoint (`agentcore_app.py`)


    - Wrap core agent logic with `@app.entrypoint` decorator using BedrockAgentCoreApp
    - Accept payload with action type (upload, start_session, submit_answer, get_explanation, get_results)
    - Route to appropriate handler functions
    - _Requirements: 5.3_
  - [x] 8.2 Create Dockerfile and deployment configuration


    - Write Dockerfile for containerized deployment
    - Create deployment script using `agentcore configure` and `agentcore launch`
    - _Requirements: 5.3_

- [x] 9. Final Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Set up Terraform infrastructure project






  - [x] 10.1 Initialize Terraform project structure

    - Create `infra/` directory with `main.tf`, `ecs.tf`, `alb.tf`, `iam.tf`, `ecr.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars`, and `backend.tf`
    - Configure AWS provider with `us-east-1` region
    - Define input variables: `aws_region`, `app_name`, `container_port`, `cpu`, `memory`, `min_capacity`, `max_capacity`
    - _Requirements: 5.3_


  - [x] 10.2 Implement VPC and networking (`main.tf`)

    - Define VPC with 2 AZs, public subnets (for ALB), private subnets (for ECS tasks)
    - Add NAT gateway for outbound access from private subnets (Bedrock API calls)
    - Add internet gateway for public subnets
    - Configure route tables for public and private subnets
    - Configure security groups: ALB allows inbound 80/443; ECS allows inbound only from ALB SG
    - _Requirements: 5.3_


  - [x] 10.3 Implement ECR repository (`ecr.tf`)

    - Create `aws_ecr_repository` with image tag mutability set to MUTABLE
    - Add lifecycle policy to keep last 5 images
    - Output the repository URL
    - _Requirements: 5.3_


  - [x] 10.4 Implement IAM roles (`iam.tf`)

    - Create ECS task execution role with `AmazonECSTaskExecutionRolePolicy` and SSM read access
    - Create ECS task role with `bedrock:InvokeModel` permission scoped to the Claude model ARN
    - _Requirements: 5.3_


  - [x] 10.5 Implement ECS Fargate service with ALB (`ecs.tf`, `alb.tf`)

    - Create ECS cluster
    - Define task definition: 512 CPU, 1024 MB memory, container port 5000, awslogs driver
    - Wire FLASK_SECRET_KEY from SSM Parameter Store via `secrets` block
    - Set environment variable `AWS_DEFAULT_REGION=us-east-1`
    - Create ALB in public subnets with target group and listener (port 80)
    - Set health check on path `/` with 30-second interval
    - Create ECS service with desired count 1, assign to private subnets
    - Configure auto-scaling: min 1, max 3, target 70% CPU utilization
    - Add CloudWatch log group with 30-day retention
    - _Requirements: 5.3_


  - [x] 10.6 Update Dockerfile for production Flask deployment

    - Add `templates/` directory to the COPY step
    - Change entrypoint to run Flask via gunicorn on port 5000
    - Add gunicorn to `requirements.txt`
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 11. Checkpoint - Verify Terraform validates correctly
  - Ensure `terraform init` and `terraform validate` pass, ask the user if questions arise.
