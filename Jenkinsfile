// Jenkinsfile - Django 项目自动化构建流水线

pipeline {
    agent any  // 在任何可用的节点上运行
    
    environment {
        // 从 Jenkins 凭据中获取 AWS 访问密钥
        AWS_ACCESS_KEY_ID = credentials('aws-access-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('aws-secret-access-key')
        AWS_REGION = 'us-east-1'
        
        // ECR 仓库信息 - 需要替换为您的实际仓库 URL
        ECR_REPOSITORY = '053735103612.dkr.ecr.us-east-1.amazonaws.com/my-django-app-dev'
        IMAGE_TAG = 'latest'
    }
    
    stages {
        // 阶段 1: 获取代码
        stage('Checkout') {
            steps {
                echo '从 Git 仓库拉取代码...'
                checkout scm  // 自动拉取触发构建的代码
            }
        }
        
        // 阶段 2: 安装依赖和测试
        stage('Test') {
            steps {
                echo '安装依赖和运行测试...'
                sh '''
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                    # 运行 Django 测试
                    python manage.py test --noinput
                '''
            }
        }
        
        // 阶段 3: 构建 Docker 镜像
        stage('Build') {
            steps {
                echo '构建 Docker 镜像...'
                sh '''
                    docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
                    docker images
                '''
            }
        }
        
        // 阶段 4: 安全扫描
        stage('Security Scan') {
            steps {
                echo '扫描镜像安全漏洞...'
                sh '''
                    # 使用 trivy 进行安全扫描（可选）
                    docker run --rm \\
                    -v /var/run/docker.sock:/var/run/docker.sock \\
                    aquasec/trivy image --exit-code 0 --severity HIGH,CRITICAL \\
                    ${ECR_REPOSITORY}:${IMAGE_TAG} || true
                '''
            }
        }
        
        // 阶段 5: 推送镜像到 ECR
        stage('Push to ECR') {
            steps {
                echo '推送镜像到 ECR...'
                sh '''
                    # 登录 ECR
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY}
                    
                    # 推送镜像
                    docker push ${ECR_REPOSITORY}:${IMAGE_TAG}
                    
                    echo "镜像已推送到: ${ECR_REPOSITORY}:${IMAGE_TAG}"
                '''
            }
        }
    }
    
    // 构建后操作
    post {
        always {
            echo '清理工作空间...'
            cleanWs()  // 清理 Jenkins 工作空间
        }
        success {
            echo '✅ 构建成功！'
            // 可以在这里添加成功通知，如 Slack、邮件等
        }
        failure {
            echo '❌ 构建失败！'
            // 可以在这里添加失败通知
        }
    }
}
