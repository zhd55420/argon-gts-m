pipeline {
    agent {
        docker {
            image 'python:3.9'
            args '-u root:root'
        }
    }
    
    environment {
        AWS_REGION = 'us-east-1'
        ECR_REPOSITORY = '053735103612.dkr.ecr.us-east-1.amazonaws.com/my-django-app-dev'
        IMAGE_TAG = 'latest'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Install System Dependencies') {
            steps {
                sh '''
                    echo "安装系统构建工具和 AWS CLI..."
                    apt-get update
                    apt-get install -y gcc g++ python3-dev curl unzip
                    
                    # 安装 AWS CLI v2
                    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                    unzip awscliv2.zip
                    ./aws/install
                    rm -rf awscliv2.zip ./aws
                    
                    # 验证安装
                    aws --version
                    echo "构建工具和 AWS CLI 安装完成"
                '''
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    python --version
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    python manage.py test --noinput
                '''
            }
        }
        
        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
                    echo "镜像构建完成: ${ECR_REPOSITORY}:${IMAGE_TAG}"
                '''
            }
        }
        
        stage('Push to ECR') {
            steps {
                withCredentials([
                    string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                        # 配置 AWS CLI
                        aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
                        aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
                        aws configure set region $AWS_REGION
                        aws configure set output json
                        
                        # 验证 AWS 配置
                        echo "验证 AWS 身份..."
                        aws sts get-caller-identity
                        
                        # 登录 ECR
                        echo "登录到 ECR..."
                        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
                        
                        # 推送镜像
                        echo "推送镜像到 ECR..."
                        docker push $ECR_REPOSITORY:$IMAGE_TAG
                        
                        echo "✅ 镜像已成功推送到: $ECR_REPOSITORY:$IMAGE_TAG"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo '✅ 构建成功！'
        }
        failure {
            echo '❌ 构建失败！'
        }
    }
}
