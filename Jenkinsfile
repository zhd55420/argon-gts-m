// 修复后的 Jenkinsfile - 使用 Docker 代理
pipeline {
    agent {
        docker {
            image 'python:3.9-slim'  // 使用官方 Python 镜像
            args '-u root:root --privileged'  // 以 root 用户运行，避免权限问题
        }
    }
    
    environment {
        AWS_REGION = 'us-east-1'
        // 使用你的实际 ECR 仓库 URL
        ECR_REPOSITORY = '123456789012.dkr.ecr.us-east-1.amazonaws.com/my-django-app-dev'
        IMAGE_TAG = 'latest'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo '从 Git 仓库拉取代码...'
                checkout scm
            }
        }
        
        stage('Test') {
            steps {
                echo '安装依赖和运行测试...'
                sh '''
                    python --version
                    pip --version
                    pip install -r requirements.txt
                    python manage.py test --noinput
                '''
            }
        }
        
        stage('Build Docker Image') {
            steps {
                echo '构建 Docker 镜像...'
                sh '''
                    docker --version
                    docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
                    docker images | grep ${ECR_REPOSITORY}
                '''
            }
        }
        
        stage('Push to ECR') {
            steps {
                echo '推送镜像到 ECR...'
                withCredentials([
                    string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                        # 配置 AWS CLI
                        aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
                        aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
                        aws configure set region $AWS_REGION
                        
                        # 登录 ECR
                        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
                        
                        # 推送镜像
                        docker push $ECR_REPOSITORY:$IMAGE_TAG
                        
                        echo "✅ 镜像已推送到: $ECR_REPOSITORY:$IMAGE_TAG"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            echo '清理工作空间...'
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
