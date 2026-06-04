# Implementation Plan

- [ ] 1. Implement exam library data models and client
  - [ ] 1.1 Create `exam_mockup_agent/library.py` with data models and S3 client
    - Implement `ExamEntry` dataclass with fields: id, name, provider, description, file_path, question_count
    - Implement `ExamManifest` dataclass with `exams: list[ExamEntry]`, `serialize()` and `deserialize()` methods
    - Implement `get_library_config()` reading `EXAM_LIBRARY_BUCKET` and `EXAM_LIBRARY_PREFIX` (default `exams/`) from environment
    - Implement `fetch_manifest(bucket, prefix)` using boto3 to download and parse `index.json`
    - Implement `download_exam(bucket, file_path)` to download XLSX to a temp file and return the path
    - Define `LibraryError` exception class for S3/manifest errors
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 4.1, 4.2_

  - [ ]* 1.2 Write property test: Manifest Serialization Round-Trip
    - **Property 1: Manifest Serialization Round-Trip**
    - **Validates: Requirements 4.3**
    - Use Hypothesis to generate random valid ExamManifest objects, serialize to JSON, deserialize back, assert equivalence

  - [ ]* 1.3 Write property test: Invalid Manifest Entry Rejection
    - **Property 2: Invalid Manifest Entry Rejection**
    - **Validates: Requirements 2.2, 4.2**
    - Use Hypothesis to generate manifest entry JSON objects with random subsets of required fields removed, verify validation raises error identifying missing fields

  - [ ]* 1.4 Write unit tests for library configuration
    - Test `get_library_config()` returns (None, "exams/") when EXAM_LIBRARY_BUCKET is unset
    - Test `get_library_config()` returns (bucket, prefix) when both env vars are set
    - Test `get_library_config()` returns (bucket, "exams/") when only bucket is set
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 2. Implement Flask routes and browse template
  - [ ] 2.1 Add browse exams route and template
    - Create `/browse` route in `flask_app.py` that calls `fetch_manifest()` and renders exam list
    - Create `templates/browse.html` displaying exam cards with name, provider, description, question count, and "Start" button
    - Handle errors (bucket not configured, manifest missing) with flash messages and fallback to upload
    - _Requirements: 1.1, 1.2, 1.3, 2.3_

  - [ ] 2.2 Add select-exam route
    - Create `/select-exam/<exam_id>` POST route that downloads the selected exam XLSX from S3
    - Parse the downloaded XLSX using existing `parse_xlsx()`
    - Store parsed questions in session and redirect to mode selection
    - Handle missing file errors gracefully
    - _Requirements: 1.4, 2.4_

  - [ ] 2.3 Update home page to show "Browse Exams" option
    - Add conditional "Browse Exams" button/link to `templates/home.html` (visible only when library is configured)
    - Pass `library_available` flag from the home route based on `get_library_config()`
    - _Requirements: 1.1, 3.3_

- [ ] 3. Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Add Terraform S3 infrastructure
  - [ ] 4.1 Create S3 bucket resource (`infra/s3.tf`)
    - Create `aws_s3_bucket` with versioning enabled
    - Add bucket policy for private access
    - Output the bucket name
    - _Requirements: 5.1_

  - [ ] 4.2 Update IAM and ECS configuration for S3 access
    - Add `s3:GetObject` and `s3:ListBucket` permissions to the ECS task role in `iam.tf`
    - Add `EXAM_LIBRARY_BUCKET` environment variable to the ECS task definition in `ecs.tf`
    - _Requirements: 5.2, 5.3_

- [ ] 5. Final Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.
