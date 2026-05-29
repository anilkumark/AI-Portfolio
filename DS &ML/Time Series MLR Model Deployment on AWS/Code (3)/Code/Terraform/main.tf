############################################
# EC2 INSTANCE CONFIGURATION
############################################
# Default VPC
data "aws_vpc" "default" {
  default = true
}

# Default Subnet
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group - allow SSH
resource "aws_security_group" "allow_ssh" {
  name        = "allow_ssh_simple_security_terraform"
  description = "Allow SSH inbound traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Generate SSH key pair
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Register key in AWS
resource "aws_key_pair" "keypair" {
  key_name   = "terraform-ec2-key-gaussian"
  public_key = tls_private_key.ssh_key.public_key_openssh
}

# Save private key locally
resource "local_file" "private_key_pem" {
  content         = tls_private_key.ssh_key.private_key_pem
  filename        = "${path.module}/terraform-ec2-key-gaussian.pem"
  file_permission = "0600"
}

############################################
# IAM ROLE FOR EC2
############################################
resource "aws_iam_role" "ec2_role" {
  name = "ec2-gaussian-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

############################################
# CUSTOM LIGHTSAIL POLICY
############################################
resource "aws_iam_policy" "lightsail_full_access" {
  name        = "LightsailFullAccessForEC2"
  description = "Custom policy for allowing EC2 access to Lightsail APIs"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = "lightsail:*",
      Resource = "*"
    }]
  })
}

############################################
# ATTACH AWS MANAGED POLICIES
############################################

# Amazon S3 Full Access
resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# ECR Power User
resource "aws_iam_role_policy_attachment" "ecr_power_user" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

############################################
# ATTACH CUSTOM LIGHTSAIL POLICY
############################################
resource "aws_iam_role_policy_attachment" "lightsail_policy_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.lightsail_full_access.arn
}

############################################
# INSTANCE PROFILE
############################################
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2-gaussian-instance-profile"
  role = aws_iam_role.ec2_role.name
}


# EC2 Instance
resource "aws_instance" "ec2_instance" {
  ami                    = "ami-0ecb62995f68bb549"
  instance_type          = "t2.xlarge"
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.allow_ssh.id]
  key_name               = aws_key_pair.keypair.key_name
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  # Add EBS storage
  root_block_device {
    volume_type = "gp3"
    volume_size = 32
  }

  tags = {
    Name = "Gaussian-project-instance"
  }
}

######################################
# LIGHTSAIL CONTAINER SERVICES
######################################
resource "null_resource" "lightsail_service" {
  provisioner "local-exec" {
    command = "aws lightsail create-container-service --service-name flask-service --power small --scale 1"
  }
}
