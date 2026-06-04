terraform {
  backend "s3" {
    bucket         = "exam-mockup-agent-tfstate"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "exam-mockup-agent-tflock"
    encrypt        = true
  }
}
